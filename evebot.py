import discord
import logging
import asyncio
import configparser
import aiohttp
import json


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

config = configparser.ConfigParser()
config.read('config.ini')

API_VERIFIED_ID = config['default']['role_id']
token = config['default']['token']
allianceID = config['default']['allianceID']
killmail_channel_ID = config['default']['killmail_channel_ID']
api_filter_url = config['default']['api_filter_url']

headers =  {'User-Agent' : 'https://zkillboard.com/', 'Maintainer':'whitefox008@gmail.com' ,'Accept-Encoding': 'gzip'}

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='Rolling out of home since Dominion'))

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def killboard_task():
    await client.wait_until_login()

    print('Killboard_task() -> starting url fetch')
    async with aiohttp.ClientSession(headers=headers) as session:
        json_payload = await fetch(session, api_filter_url)
        jsonresponce = json.loads(json_payload)
        initfetch = jsonresponce[0]['killID'] #get initkm

        while not client.is_closed:

            json_payload = await fetch(session, 'https://zkillboard.com/api/afterKillID/%s/json/' % (initfetch))        #https://zkillboard.com/api/allianceID/99006805/afterKillID/%s/xml/
            print('Killboard_task() -> Fetching new Killmails')
            jsonresponce = json.loads(json_payload)

            try:

                initfetch = jsonresponce[0]['killID']  # keep it going lads

            except:

                print('Killboard_task() -> JSON returned no kills')
                pass

            else:
                test = ''
                for item in jsonresponce:
                    killurl = 'https://zkillboard.com/kill/' + str(item['killID']) + ' \n'
                    test = test + killurl
                await client.send_message(discord.Object(id=killmail_channel_ID), test)

            await asyncio.sleep(100)  # lets not fucking slam the server with request 50 is pretty fucking moderate


@client.event
async def on_member_join(member):
    server = member.server
    fmt = 'Welcome {0.mention} to {1.name}! to verify your account, create an api using this predefined key and then type !verify in chat! \n http://community.eveonline.com/support/api-key/CreatePredefined?accessMask=50331648'
    await client.send_message(server, fmt.format(member, server))

@client.event
async def on_message(message):
    if message.content.startswith('!verify'):
        await client.delete_message(message)
        msg = await client.send_message(message.author, '❗ **Paste your KeyID** {0.author.mention}'.format(message))
        keyid = await client.wait_for_message(author=message.author)
        k = keyid.content

        await client.edit_message(msg, '❗ **Paste your Vcode {0.author.mention}**'.format(message))
        vcode = await client.wait_for_message(author=message.author)
        v = vcode.content

        await client.edit_message(msg, '⭕ **Verifying API! {0.author.mention}**'.format(message))
        await asyncio.sleep(3)

        role = discord.Object(id=API_VERIFIED_ID)

        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.eveonline.com/account/characters.xml.aspx?keyID=%s&vCode=%s' % (k, v)) as resp:
                text = await resp.text()
                if allianceID in text:
                    Pass = await client.edit_message(msg,'✅ **ACCESS GRANTED** Welcome to Wormageddon {0.author.mention}!'.format(message))
                    await asyncio.sleep(15)
                    await client.delete_message(Pass)

                    try:
                        await client.add_roles(message.author, role)

                    except:
                        exc = await client.edit_message(msg, 'You passed Verification but you are a admin or already have the role and therefor cant be added to the role! ')
                        await asyncio.sleep(15)
                        await client.delete_message(exc)

                else:
                    Fail = await client.edit_message(msg,'❌ ***{0.author.mention} you have entered a invalid api you dork try again using !verify*** ❌ \n https://vgy.me/5nObgz.jpg'.format(message))
                    await asyncio.sleep(25)
                    await client.delete_message(Fail)


client.loop.create_task(killboard_task())
client.run(token)
