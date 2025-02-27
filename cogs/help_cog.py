import discord
from discord.ext import commands
import logging

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug("[Help] Initialized")

    def get_all_models(self):
        """Get all models and their details from registered cogs"""
        models = []
        vision_models = []
        
        for cog in self.bot.cogs.values():
            if hasattr(cog, 'name') and hasattr(cog, 'model') and cog.name != "Help":
                model_info = {
                    'name': cog.name,
                    'nickname': getattr(cog, 'nickname', cog.name),
                    'trigger_words': getattr(cog, 'trigger_words', []),
                    'supports_vision': getattr(cog, 'supports_vision', False),
                    'model': getattr(cog, 'model', 'Unknown'),
                    'provider': getattr(cog, 'provider', 'Unknown')
                }
                
                if model_info['supports_vision']:
                    vision_models.append(model_info)
                else:
                    models.append(model_info)
                    
        return vision_models, models

    def format_model_list(self, vision_models, models):
        """Format the model list for display"""
        help_text = """**🤖 Available AI Models**\n\n"""
        
        # Add vision-capable models
        if vision_models:
            help_text += "**Vision-Capable Models:**\n"
            for model in vision_models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n"
                help_text += f"  *Special:* Can analyze images and provide descriptions\n\n"
        
        # Add language models
        if models:
            help_text += "**Large Language Models:**\n"
            for model in models:
                triggers = ", ".join(model['trigger_words'])
                help_text += f"• **{model['name']}** [{model['model']} via {model['provider']}]\n"
                help_text += f"  *Triggers:* {triggers}\n\n"
                
        return help_text

    def format_simple_model_list(self, vision_models, models):
        """Format a simple model list with just names and models"""
        model_list = "**Available Models:**\n"
        
        # Add vision models with a 📷 indicator
        for model in vision_models:
            model_list += f"📷 {model['name']} - {model['model']}\n"
            
        # Add regular models
        for model in models:
            model_list += f"💬 {model['name']} - {model['model']}\n"
            
        return model_list

    @commands.command(name="splintertree_help", aliases=["help"])
    async def help_command(self, ctx):
        """Send a comprehensive help message with all available features"""
        try:
            # Get dynamically loaded models
            vision_models, models = self.get_all_models()
            model_list = self.format_model_list(vision_models, models)
            
            # Add special features and tips
            help_message = f"""{model_list}
    **📝 Special Features:**
    • **Response Reroll** - Click the 🎲 button to get a different response
    • **Private Responses** - Surround your message with ||spoiler tags|| to get a DM response
    • **Context Memory** - Models remember conversation history for better context
    • **Image Analysis** - Use vision-capable models for image descriptions and analysis
    • **Custom System Prompts** - Set custom prompts for each AI agent
    • **Agent Cloning** - Create custom variants of existing agents with unique system prompts
    • **Chat Summaries** - Automatically summarizes chat history for better context

    **💡 Tips:**
    1. Models will respond when you mention their trigger words
    2. Each model has unique strengths - try different ones for different tasks
    3. For private responses, format your message like: ||your message here||
    4. Images are automatically analyzed when sent with messages
    5. Use the reroll button to get alternative responses if needed
    6. Chat summaries help maintain context over longer conversations

    **Available Commands:**
    • `splintertree_help` or `help` - Show this help message
    • `!listmodels` - Show all available models (simple list)
    • `!list_agents` - Show all available agents with detailed info (formatted embed)
    • `!uptime` - Show how long the bot has been running
    • `!set_system_prompt agent prompt` - Set a custom system prompt for an AI agent
    • `!reset_system_prompt agent` - Reset an AI agent's system prompt to default
    • `!clone_agent agent new_name system_prompt` - Create a new agent based on an existing one (Admin only)
    • `!setcontext size` - Set the number of previous messages to include in context (Admin only)
    • `!getcontext` - View current context window size
    • `!resetcontext` - Reset context window to default size (Admin only)
    • `!clearcontext [hours]` - Clear conversation history, optionally specify hours (Admin only)
    • `!summarize` - Force create a summary for the current channel (Admin only)
    • `!getsummaries [hours]` - View chat summaries for specified hours (default: 24)
    • `!clearsummaries [hours]` - Clear chat summaries, optionally specify hours (Admin only)

    **System Prompt Variables:**
    When setting custom system prompts, you can use these variables:
    • {{MODEL_ID}} - The AI model's name
    • {{USERNAME}} - The user's Discord display name
    • {{DISCORD_USER_ID}} - The user's Discord ID
    • {{TIME}} - Current local time
    • {{TZ}} - Local timezone
    • {{SERVER_NAME}} - Current Discord server name
    • {{CHANNEL_NAME}} - Current channel name
    """
            
            for msg in [help_message[i:i + 2000] for i in range(0, len(help_message), 2000)]:
                await ctx.send(msg)

            logging.info(f"[Help] Sent help message to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending help message: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the help message. Please try again later.")

    @commands.command(name="listmodels")
    async def list_models_command(self, ctx):
        """Send a simple list of all available models"""
        try:
            vision_models, models = self.get_all_models()
            model_list = self.format_simple_model_list(vision_models, models)
            await ctx.send(model_list)
            logging.info(f"[Help] Sent model list to user {ctx.author.name}")
        except Exception as e:
            logging.error(f"[Help] Error sending model list: {str(e)}", exc_info=True)
            await ctx.send("An error occurred while fetching the model list. Please try again later.")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
