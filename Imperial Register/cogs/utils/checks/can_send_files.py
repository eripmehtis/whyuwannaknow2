from discord.ext.commands import check, CheckFailure


class CantSendFiles(CheckFailure):
    pass


def can_send_files():
    async def predicate(ctx):
        if ctx.guild == None:
            return True
        if ctx.guild.me.permissions_in(ctx.channel).attach_files:
            return True
        raise CantSendFiles()
    return check(predicate)
