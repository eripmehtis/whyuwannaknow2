from traceback import format_exc
from asyncio import iscoroutine

from aiohttp import ClientSession
from discord import Member, Message, Activity, ActivityType, User, Status
from discord.ext.commands import command, Context, group, NotOwner

from cogs.utils.custom_bot import CustomBot
from cogs.utils.family_tree.family_tree_member import FamilyTreeMember
from cogs.utils.customised_tree_user import CustomisedTreeUser


class CalebOnly(object):
    '''
    The parentage cog
    Handles the adoption of parents
    '''

    def __init__(self, bot:CustomBot):
        self.bot = bot
        self.last_tree = None
        self.stream = None  # May be channel/ID


    def __local_check(self, ctx:Context):
        if ctx.author.id in self.bot.config['owners']:
            return True
        raise NotOwner


    @property
    def stream_channel(self):
        channel_id = self.bot.config['stream_channel']
        channel = self.bot.get_channel(channel_id)
        return channel


    @command(aliases=['s'])
    async def send(self, ctx:Context, *, content:str):
        '''
        Sends content to the current stream channel
        '''

        if self.stream == None:
            await ctx.send("No stream currently set up.")
            return
        await self.stream.send(content)


    @command(aliases=['cs'])
    async def channelstream(self, ctx:Context, channel_id:int=None):
        '''
        Streams a channel's output to the chat log
        '''

        if channel_id == None:
            self.stream = None
            await ctx.send("Cleared stream.")
            return
        self.stream = self.bot.get_channel(channel_id)
        # self.stream = channel
        await ctx.send(f"Channel set to `{self.stream.name}` (`{self.stream.id}`)")


    async def on_message(self, message:Message):
        '''
        Log streamed messages to channel
        '''

        if not message.channel:
            return
        if not self.stream:
            return
        if not self.stream_channel:
            return
        if message.channel.id == self.stream.id:
            attachments = [i.url for i in message.attachments]
            if message.content:
                text = f"**Streamed Message** | User: `{message.author!s}` (`{message.author.id}`)\nContent: `{message.content}`"
            else:
                text = f"**Streamed Message** | User: `{message.author!s}` (`{message.author.id}`)\nNo text content in message."
            if attachments:
                text += '\nAttachments: ' + ', '.join(attachments)
            await self.stream_channel.send(text) 


    @command(aliases=['pm', 'dm'])
    async def message(self, ctx:Context, user:User, *, content:str):
        '''
        Messages a user the given content
        '''

        await user.send(content)


    @command()
    async def forcemarry(self, ctx:Context, user_a:User, user_b:User):
        '''
        Marries the two specified users
        '''

        async with self.bot.database() as db:
            try:
                await db.marry(user_a, user_b)
            except Exception as e:
                return  # Only thrown if two people try to marry at once, so just return
        me = FamilyTreeMember.get(user_a.id)
        me._partner = user_b.id 
        them = FamilyTreeMember.get(user_b.id)
        them._partner = user_a.id
        await ctx.send("Consider it done.")


    @command()
    async def forceadopt(self, ctx:Context, parent:User, child:User):
        '''
        Adds the child to the specified parent
        '''

        async with self.bot.database() as db:
            try:
                await db('INSERT INTO parents (parent_id, child_id) VALUES ($1, $2)', parent.id, child.id)
            except Exception as e:
                return  # Only thrown when multiple people do at once, just return
        me = FamilyTreeMember.get(parent.id)
        me._children.append(child.id)
        them = FamilyTreeMember.get(child.id)
        them._parent = parent.id
        await ctx.send("Consider it done.")


    @command()
    async def ev(self, ctx:Context, *, content:str):
        '''
        Runs some text through Python's eval function
        '''

        try:
            ans = eval(content, globals(), locals())
        except Exception as e:
            await ctx.send('```py\n' + format_exc() + '```')
            return
        if iscoroutine(ans):
            ans = await ans
        await ctx.send('```py\n' + str(ans) + '```')


    @command()
    async def nev(self, ctx:Context, *, content:str):
        '''
        Runs some text through Python's eval function
        '''

        try:
            ans = eval(content, globals(), locals())
        except Exception as e:
            await ctx.send('```py\n' + format_exc() + '```')
            return
        if iscoroutine(ans):
            ans = await ans
        await ctx.send(str(ans))


    @command(aliases=['rld'])
    async def reload(self, ctx:Context, *cog_name:str):
        '''
        Unloads a cog from the bot
        '''

        self.bot.unload_extension('cogs.' + '_'.join([i for i in cog_name]))
        try:
            self.bot.load_extension('cogs.' + '_'.join([i for i in cog_name]))
        except Exception as e:
            await ctx.send('```py\n' + format_exc() + '```')
            return
        await ctx.send('Cog reloaded.')


    @command()
    async def runsql(self, ctx:Context, *, content:str):
        '''
        Runs a line of SQL into the sparcli database
        '''

        async with self.bot.database() as db:
            x = await db(content) or 'No content.'
        if type(x) in [str, type(None)]:
            await ctx.send(x)
            return

        # Get the results into groups
        column_headers = list(x[0].keys())
        grouped_outputs = {}
        for i in column_headers:
            grouped_outputs[i] = []
        for guild_data in x:
            for i, o in guild_data.items():
                grouped_outputs[i].append(str(o))

        # Everything is now grouped super nicely
        # Now to get the maximum length of each column and add it as the last item
        for key, item_list in grouped_outputs.items():
            max_len = max([len(i) for i in item_list + [key]])
            grouped_outputs[key].append(max_len)

        # Format the outputs and add to a list
        key_headers = []
        temp_output = []
        for key, value in grouped_outputs.items():
            # value is a list of unformatted strings
            key_headers.append(format(key, '<' + str(value[-1])))
            formatted_values = [format(i, '<' + str(value[-1])) for i in value[:-1]]
            # string_value = '|'.join(formatted_values)
            temp_output.append(formatted_values)
        key_string = '|'.join(key_headers)

        # Rotate the list because apparently I need to
        output = []
        for i in range(len(temp_output[0])):
            temp = []
            for o in temp_output:
                temp.append(o[i])
            output.append('|'.join(temp))

        # Add some final values before returning to the user
        line = '-' * len(key_string)
        output = [key_string, line] + output 
        string_output = '\n'.join(output)
        await ctx.send('```\n{}```'.format(string_output))


    @group()
    async def profile(self, ctx:Context):
        '''
        A parent group for the different profile commands
        '''

        pass


    @profile.command(aliases=['username'])
    async def name(self, ctx:Context, *, username:str):
        '''
        Lets you change the username of the bot
        '''

        if len(username) > 32:
            await ctx.send('That username is too long to be compatible with Discord.')
            return 

        await self.bot.user.edit(username=username)
        await ctx.send('Done.')


    @profile.command(aliases=['photo', 'image', 'avatar'])
    async def picture(self, ctx:Context, *, image_url:str=None):
        '''
        Lets you change the username of the bot
        '''

        if image_url == None:
            try:
                image_url = ctx.message.attachments[0].url 
            except IndexError:
                await ctx.send("You need to provide an image.")
                return

        async with ClientSession(loop=self.bot.loop) as session:
            async with session.get(image_url) as r:
                image_content = await r.read()
        await self.bot.user.edit(avatar=image_content)
        await ctx.send('Done.')


    @profile.command(aliases=['game'])
    async def activity(self, ctx:Context, activity_type:str, *, name:str=None):
        '''
        Changes the activity of the bot
        '''

        if name:
            activity = Activity(name=name, type=getattr(ActivityType, activity_type.lower()))
        else:
            await self.bot.set_default_presence()
            return
        await self.bot.change_presence(activity=activity, status=self.bot.guilds[0].me.status)


    @profile.command()
    async def status(self, ctx:Context, status:str):
        '''
        Changes the bot's status
        '''

        status_o = getattr(Status, status.lower())
        await self.bot.change_presence(activity=self.bot.guilds[0].me.activity, status=status_o)


def setup(bot:CustomBot):
    x = CalebOnly(bot)
    bot.add_cog(x)


