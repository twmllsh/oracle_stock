import discord
from discord.ext import commands
from django.conf import settings
# 봇 토큰 설정

class MyDiscordBot(commands.Bot):

    def __init__(self):
        self.command_prefix = '!'
        # Intents 설정
        intents = discord.Intents.default()
        intents.message_content = True  # 메시지 내용에 접근할 수 있도록 설정
        
        # commands.Bot 초기화
        super().__init__(command_prefix=self.command_prefix, intents=intents)
        self.TOKEN = settings.MYENV("DISCORD_BOT_TOKEN")

        
        self.add_command(self.hello_command)

        
    async def on_ready(self):
        print(f'Logged in as {self.user}!')
        
    async def on_message(self, message):
        # 봇 자신의 메시지에는 반응하지 않음
        if message.author == self.user:
            return

        # 특정 메시지를 받으면 응답
        if message.content.lower() == 'hello':
            await message.channel.send('Hello there! 👋')

        # 명령어 처리
        result = await self.process_commands(message)
        if result :
            await message.channel.send('succeed command from message')
        
        
    # 특정 커맨드 (예: !hello)를 받으면 응답하는 명령어
    @commands.command(name='hello')
    async def hello_command(self, ctx):
        await ctx.send('Hello! How can I assist you?')

    def run_bot(self):
        self.run(self.TOKEN)
        
        

# 봇 실행
if __name__ == '__main__':
    if not settings.DEBUG:
        bot = MyDiscordBot()
        bot.run_bot()