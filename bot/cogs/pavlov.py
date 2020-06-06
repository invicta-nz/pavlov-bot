import discord
from discord.ext import commands

from bot.utils import config, servers
from pavlov import PavlovRCON

# Admin – GiveItem, GiveCash, GiveTeamCash, SetPlayerSkin
# Mod – Ban, Kick, Unban, RotateMap, SwitchTeam
# Captain – SwitchMap, ResetSND
# Everyone - RefreshList, InspectPlayer, ServerInfo
# Ban – Told to fuck off


MODERATOR_ROLE = "Mod-{}"
CAPTAIN_ROLE = "Captain-{}"


async def exec_server_command(server_name: str, command: str):
    server = servers.get(server_name)
    pavlov = PavlovRCON(server.get("ip"), server.get("port"), server.get("password"))
    return await pavlov.send(command)


async def check_banned(ctx):
    pass


async def check_perm_admin(ctx, server_name: str, sub_check=False):
    """ Admin permissions are stored per server in the servers.json """
    server = servers.get(server_name)
    if ctx.author.id not in server.get("admins", []):
        if not sub_check:
            await ctx.send(
                embed=discord.Embed(description=f"This command is only for Admins.")
            )
        return False
    return True


async def check_perm_moderator(ctx, server_name: str, sub_check=False):
    if await check_perm_admin(ctx, server_name, sub_check=True):
        return True
    role_name = MODERATOR_ROLE.format(server_name)
    role = discord.utils.get(ctx.author.roles, name=role_name)
    if role is None:
        if not sub_check:
            await ctx.send(
                embed=discord.Embed(description=f"This command is only for Moderators.")
            )
        return False
    return True


async def check_perm_captain(ctx, server_name: str):
    if await check_perm_moderator(ctx, server_name, sub_check=True):
        return True
    role_name = CAPTAIN_ROLE.format(server_name)
    role = discord.utils.get(ctx.author.roles, name=role_name)
    if role is None:
        await ctx.send(
            embed=discord.Embed(description=f"This command is only for Captains.")
        )
        return False
    return True


class Pavlov(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{type(self).__name__} Cog ready.")

    async def cog_command_error(self, ctx, error):
        embed = discord.Embed()
        if isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"⚠️ Missing some required arguments.\nPlease use `{config.prefix}help` for more info!"
        elif isinstance(error.original, servers.ServerNotFoundError):
            embed.description = (
                f"⚠️ Server `{error.original.server_name}` not found.\n "
                f"Please try again or use `{config.prefix}servers` to list the available servers."
            )
        elif isinstance(error.original, ConnectionRefusedError):
            embed.description = f"Failed to establish connection to server, please try again later or contact an admin."
        else:
            raise error
        await ctx.send(embed=embed)

    async def cog_before_invoke(self, ctx):
        await ctx.trigger_typing()

    @commands.command()
    async def servers(self, ctx):
        """Lists available servers"""
        server_names = servers.get_names()
        embed = discord.Embed(
            title="Servers", description="\n- ".join([""] + server_names)
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx, server_name: str):
        """Shows ServerInfo

        **Usage**: `{prefix}serverinfo <server_name>`
        **Example**: `{prefix}serverinfo rush`
        """

        data = await exec_server_command(server_name, "ServerInfo")
        server_info = data.get("ServerInfo")

        embed = discord.Embed(description=f"**ServerInfo** for `{server_name}`")
        embed.add_field(
            name="Server Name", value=server_info.get("ServerName"), inline=False
        )
        embed.add_field(name="Round State", value=server_info.get("RoundState"))
        embed.add_field(name="Players", value=server_info.get("PlayerCount"))
        embed.add_field(name="Game Mode", value=server_info.get("GameMode"))
        embed.add_field(name="Map Label", value=server_info.get("MapLabel"))
        await ctx.send(embed=embed)

    @commands.command()
    async def players(self, ctx, server_name: str):
        """Shows RefreshList

        **Usage**: `{prefix}players <server_name>`
        **Example**: `{prefix}players rush`
        """
        data = await exec_server_command(server_name, "RefreshList")
        player_list = data.get("PlayerList")
        embed = discord.Embed(description=f"**Active players** on `{server_name}`:\n")
        if len(player_list) == 0:
            embed.description = f"Currently no active players on `{server_name}`"
        for player in player_list:
            embed.description += (
                f"\n - {player.get('Username', '')} <{player.get('UniqueId')}>"
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def playerinfo(self, ctx, player_id: str, server_name: str):
        """Shows PlayerInfo

        **Usage**: `{prefix}playerinfo <player_id> <server_name>`
        **Example**: `{prefix}playerinfo 89374583439127 rush`
        """
        data = await exec_server_command(server_name, f"InspectPlayer {player_id}")
        player_info = data.get("PlayerInfo")
        if not player_info:
            embed = discord.Embed(description=f"Player <{player_id}> not found.")
        else:
            embed = discord.Embed(description=f"**Player info** for <{player_id}>")
            embed.add_field(name="Name", value=player_info.get("PlayerName"))
            embed.add_field(name="UniqueId", value=player_info.get("UniqueId"))
            embed.add_field(name="KDA", value=player_info.get("KDA"))
            embed.add_field(name="Cash", value=player_info.get("Cash"))
            embed.add_field(name="TeamId", value=player_info.get("TeamId"))
        await ctx.send(embed=embed)

    @commands.command()
    async def switchmap(self, ctx, map_name: str, game_mode: str, server_name: str):
        """Runs SwitchMap

        **Usage**: `{prefix}switchmap <map_name> <game_mode> <server_name>`
        **Example**: `{prefix}switchmap 89374583439127 rush`
        """
        if not await check_perm_captain(ctx, server_name):
            return
        data = await exec_server_command(
            server_name, f"SwitchMap {map_name} {game_mode}"
        )
        switch_map = data.get("SwitchMap")
        if not switch_map:
            embed = discord.Embed(
                description=f"**Failed** to switch map to {map_name} with game mode {game_mode}"
            )
        else:
            embed = discord.Embed(
                description=f"Switched map to {map_name} with game mode {game_mode}"
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def resetsnd(self, ctx, server_name: str):
        """Runs ResetSND

        **Usage**: `{prefix}resetsnd <server_name>`
        **Example**: `{prefix}resetsnd rush`
        """
        if not await check_perm_captain(ctx, server_name):
            return
        data = await exec_server_command(server_name, "ResetSND")
        reset_snd = data.get("ResetSND")
        if not reset_snd:
            embed = discord.Embed(description=f"**Failed** reset SND")
        else:
            embed = discord.Embed(description=f"SND successfully reset")
        await ctx.send(embed=embed)

    @commands.command()
    async def switchteam(self, ctx, unique_id: str, team_id: str, server_name: str):
        """Runs SwitchTeam

        **Usage**: `{prefix}switchteam <player_id> <team_id> <server_name>`
        **Example**: `{prefix}resetsnd 89374583439127 0 rush`
        """
        if not await check_perm_captain(ctx, server_name):
            return
        data = await exec_server_command(
            server_name, f"SwitchTeam {unique_id} {team_id}"
        )
        switch_team = data.get("SwitchTeam")
        if not switch_team:
            embed = discord.Embed(
                description=f"**Failed** to switch <{unique_id}> to team {team_id}"
            )
        else:
            embed = discord.Embed(
                description=f"<{unique_id}> switched to team {team_id}"
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def rotatemap(self, ctx, server_name: str):
        """Runs RotateMap

        **Usage**: `{prefix}rotatemap <server_name>`
        **Example**: `{prefix}rotatemap rush`
        """
        if not await check_perm_moderator(ctx, server_name):
            return
        data = await exec_server_command(server_name, f"RotateMap")
        rotate_map = data.get("RotateMap")
        if not rotate_map:
            embed = discord.Embed(description=f"**Failed** to rotate map")
        else:
            embed = discord.Embed(description=f"Rotated map successfully")
        await ctx.send(embed=embed)

    @commands.command()
    async def ban(self, ctx, unique_id: str, server_name: str):
        """Runs Ban

        **Usage**: `{prefix}ban <player_id> <server_name>`
        **Example**: `{prefix}ban 89374583439127 rush`
        """
        if not await check_perm_moderator(ctx, server_name):
            return
        data = await exec_server_command(server_name, f"Ban {unique_id}")
        ban = data.get("Ban")
        if not ban:
            embed = discord.Embed(description=f"**Failed** to ban <{unique_id}>")
        else:
            embed = discord.Embed(description=f"<{unique_id}> successfully banned")
        await ctx.send(embed=embed)

    @commands.command()
    async def kick(self, ctx, unique_id: str, server_name: str):
        """Runs Kick

        **Usage**: `{prefix}kick <player_id> <server_name>`
        **Example**: `{prefix}kick 89374583439127 rush`
        """
        if not await check_perm_moderator(ctx, server_name):
            return
        data = await exec_server_command(server_name, f"Kick {unique_id}")
        kick = data.get("Kick")
        if not kick:
            embed = discord.Embed(description=f"**Failed** to kick <{unique_id}>")
        else:
            embed = discord.Embed(description=f"<{unique_id}> successfully kicked")
        await ctx.send(embed=embed)

    @commands.command()
    async def unban(self, ctx, unique_id: str, server_name: str):
        """Runs Unban

        **Usage**: `{prefix}unban <player_id> <server_name>`
        **Example**: `{prefix}unban 89374583439127 rush`
        """
        if not await check_perm_moderator(ctx, server_name):
            return
        data = await exec_server_command(server_name, f"Unban {unique_id}")
        unban = data.get("Unban")
        if not unban:
            embed = discord.Embed(description=f"**Failed** to unban <{unique_id}>")
        else:
            embed = discord.Embed(description=f"<{unique_id}> successfully unbanned")
        await ctx.send(embed=embed)

    @commands.command()
    async def giveitem(self, ctx, unique_id: str, item_id: str, server_name: str):
        """Runs GiveItem

        **Usage**: `{prefix}giveitem <player_id> <item_id> <server_name>`
        **Example**: `{prefix}giveitem 89374583439127 tazer rush`
        """
        if not await check_perm_admin(ctx, server_name):
            return
        data = await exec_server_command(server_name, f"GiveItem {unique_id} {item_id}")
        give_team = data.get("GiveItem")
        if not give_team:
            embed = discord.Embed(
                description=f"**Failed** to give {item_id} to <{unique_id}>"
            )
        else:
            embed = discord.Embed(description=f"{item_id} given to <{unique_id}>")
        await ctx.send(embed=embed)

    @commands.command()
    async def givecash(self, ctx, unique_id: str, cash_amount: str, server_name: str):
        """Runs GiveCash

        **Usage**: `{prefix}givecash <player_id> <cash_amount> <server_name>`
        **Example**: `{prefix}givecash 89374583439127 5000 rush`
        """
        if not await check_perm_admin(ctx, server_name):
            return
        data = await exec_server_command(
            server_name, f"GiveCash {unique_id} {cash_amount}"
        )
        give_cash = data.get("GiveCash")
        if not give_cash:
            embed = discord.Embed(
                description=f"**Failed** to give {cash_amount} to <{unique_id}>"
            )
        else:
            embed = discord.Embed(description=f"{cash_amount} given to <{unique_id}>")
        await ctx.send(embed=embed)

    @commands.command()
    async def giveteamcash(self, ctx, team_id: str, cash_amount: str, server_name: str):
        """Runs GiveTeamCash

        **Usage**: `{prefix}giveteamcash <player_id> <cash_amount> <server_name>`
        **Example**: `{prefix}giveteamcash 89374583439127 5000 rush`
        """
        if not await check_perm_admin(ctx, server_name):
            return
        data = await exec_server_command(
            server_name, f"GiveTeamCash {team_id} {cash_amount}"
        )
        give_team_cash = data.get("GiveTeamCash")
        if not give_team_cash:
            embed = discord.Embed(
                description=f"**Failed** to give {cash_amount} to <{team_id}>"
            )
        else:
            embed = discord.Embed(description=f"{cash_amount} given to <{team_id}>")
        await ctx.send(embed=embed)

    @commands.command()
    async def setplayerskin(self, ctx, unique_id: str, skin_id: str, server_name: str):
        """Runs SetPlayerSkin

        **Usage**: `{prefix}setplayerskin <player_id> <skin_id> <server_name>`
        **Example**: `{prefix}setplayerskin 89374583439127 clown rush`
        """
        if not await check_perm_admin(ctx, server_name):
            return
        data = await exec_server_command(
            server_name, f"SetPlayerSkin {unique_id} {skin_id}"
        )
        set_player_skin = data.get("SetPlayerSkin")
        if not set_player_skin:
            embed = discord.Embed(
                description=f"**Failed** to set <{unique_id}>'s skin to {skin_id}"
            )
        else:
            embed = discord.Embed(description=f"<{unique_id}>'s skin set to {skin_id}")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Pavlov(bot))
