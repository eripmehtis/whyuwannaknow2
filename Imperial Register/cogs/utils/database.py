from random import choice
from asyncio import create_subprocess_exec, get_event_loop

from discord import Member
from asyncpg import connect


RANDOM_CHARACTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890-_'


class DatabaseConnection(object):

    config = None
    restarting = False

    def __init__(self):
        self.db = None

    async def __aenter__(self):
        try:
            self.db = await connect(**self.config)
        except Exception as e:
            # Database connection failed - restart Postgres connection
            if self.restarting:
                raise Exception("Database in the process of restarting, please try again in a moment.")
            self.restarting = True
            restart_loop = await create_subprocess_exec(*[
                "systemctl", "restart", "postgresql"
            ], loop=get_event_loop())
            await restart_loop.wait()
            self.restarting = False
            raise e
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.db.close()
        self.db = None

    async def __call__(self, sql:str, *args):
        '''
        Runs a line of SQL using the internal database
        '''

        # Runs the SQL
        x = await self.db.fetch(sql, *args)

        # If it got something, return the dict, else None
        if x:
            return x
        if 'select' in sql.lower().split(' ') or 'returning' in sql.lower().split(' '):
            return []
        return None

    async def destroy(self, user_id:int):
        '''
        Removes a given user ID form all parts of the database
        '''

        await self('UPDATE marriages SET valid=False WHERE user_id=$1 OR partner_id=$1', user_id)
        await self('DELETE FROM parents WHERE child_id=$1 OR parent_id=$1', user_id)

    async def make_id(self, table:str, id_field:str) -> str:
        '''
        Makes a random ID that hasn't appeared in the database before for a given table
        '''

        while True:
            idnumber = ''
            for i in range(11):
                idnumber += choice(RANDOM_CHARACTERS)
            x = await self(f'SELECT * FROM {table} WHERE {id_field}=$1', idnumber)
            if not x:
                return idnumber

    async def marry(self, instigator:Member, target:Member, marriage_id:str=None):
        '''
        Marries two users together
        Remains in the Database class solely as you need the "idnumber" field.
        '''

        if marriage_id == None:
            idnumber = await self.make_id('marriages', 'marriage_id')
        else:
            idnumber = marriage_id
        # marriage_id, user_id, user_name, partner_id, partner_name, valid
        await self(
            'INSERT INTO marriages VALUES ($1, $2, $3, TRUE)',
            idnumber,
            instigator.id,
            target.id,
        )
        if marriage_id == None:
            await self.marry(target, instigator, idnumber)  # Run it again with instigator/target flipped
