import os
import asyncio
import time
import tempfile
import traceback
import discord

import config
import audio_processor

# Ensure environment variables are valid
config.validate_config()

# Configure Discord bot gateway intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Explicitly enable voice states tracking
bot = discord.Bot(intents=intents)

# Keep track of active recording sessions
# Format: { guild_id: (voice_client, start_time) }
recording_sessions = {}

async def once_done(sink: discord.sinks.Sink, channel: discord.TextChannel):
    """
    Callback function triggered when the recording stops.
    Dispatches audio processing tasks asynchronously to avoid blocking the main thread.
    """
    guild_id = channel.guild.id
    session_info = recording_sessions.pop(guild_id, None)
    
    # Calculate duration
    duration_str = "Unknown duration"
    if session_info:
        _, start_time = session_info
        duration = time.time() - start_time
        mins, secs = divmod(int(duration), 60)
        duration_str = f"{mins}m {secs}s"
        
    # Disconnect the bot from the voice channel
    if sink.vc:
        await sink.vc.disconnect()
        
    if not sink.audio_data:
        await channel.send("⚠️ Recording stopped. No audio was captured (nobody spoke).")
        return
        
    processing_msg = await channel.send(
        f"🎙️ **Recording Stopped!** (Total Duration: {duration_str})\n"
        "⏳ Processing audio files and transcribing speech locally. Please wait..."
    )
    
    # Offload audio processing and transcription to a thread pool executor
    # to prevent blocking the Discord event loop.
    loop = asyncio.get_event_loop()
    try:
        combined_path, transcripts = await loop.run_in_executor(
            None, 
            audio_processor.process_recording, 
            sink.audio_data, 
            sink.encoding
        )
    except Exception as e:
        traceback.print_exc()
        await processing_msg.edit(content=f"❌ An error occurred during audio processing: {e}")
        return
        
    # Send mixed audio file to Discord
    if combined_path and os.path.exists(combined_path):
        await channel.send(
            "💾 Here is the combined audio recording containing all speakers:",
            file=discord.File(combined_path, filename=f"channel_recording.{sink.encoding}")
        )
        try:
            os.remove(combined_path)
        except Exception:
            pass
            
    # Format and present the transcripts
    if transcripts:
        transcript_msg = "📝 **Conversation Transcript (Local Whisper):**\n\n"
        for user_id, text in transcripts.items():
            transcript_msg += f"👤 <@{user_id}>:\n> {text}\n\n"
            
        # Check if transcript message fits within Discord's 2000 character limit
        if len(transcript_msg) > 1900:
            # Save transcript to a temporary file and upload it
            temp_dir = tempfile.gettempdir()
            tx_path = os.path.join(temp_dir, f"transcript_{guild_id}.txt")
            
            txt_content = f"Discord Recording Transcript - {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            txt_content += f"Duration: {duration_str}\n"
            txt_content += "="*40 + "\n\n"
            
            for user_id, text in transcripts.items():
                member = channel.guild.get_member(user_id)
                name = member.display_name if member else f"User_{user_id}"
                txt_content += f"[{name}]:\n{text}\n\n"
                
            with open(tx_path, "w", encoding="utf-8") as f:
                f.write(txt_content)
                
            await channel.send(
                "📝 The transcript is too long to fit in a chat message, so it has been uploaded as a text file:",
                file=discord.File(tx_path, filename="transcript.txt")
            )
            try:
                os.remove(tx_path)
            except Exception:
                pass
        else:
            await channel.send(transcript_msg)
    else:
        await channel.send("📝 No speech could be transcribed from the recording.")
        
    # Clean up processing status message
    try:
        await processing_msg.delete()
    except Exception:
        pass

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user} (ID: {bot.user.id})")
    
    # Ensure Opus audio library is loaded on Linux environments
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus("libopus.so.0")
            print("🔊 Opus library loaded successfully.")
        except Exception:
            try:
                discord.opus.load_opus("libopus.so")
                print("🔊 Opus library loaded successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Could not auto-load Opus library: {e}")
    else:
        print("🔊 Opus library is loaded.")
        
    print("Slash commands registered successfully. Ready to record!")

@bot.slash_command(name="join", description="Connect the bot to your current voice channel.")
async def join(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        await ctx.respond("❌ You must be in a voice channel to use this command!")
        return
        
    # Defer interaction to prevent Discord 3-second timeout
    await ctx.defer()
        
    channel = ctx.author.voice.channel
    try:
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.respond(f"✅ Joined **{channel.name}**")
    except Exception as e:
        traceback.print_exc()
        await ctx.respond(f"❌ Failed to join voice channel: {e}")

@bot.slash_command(name="record", description="Start recording the voice channel.")
async def record(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        await ctx.respond("❌ You must be in a voice channel to start recording!")
        return
        
    # Defer interaction to prevent Discord 3-second timeout
    await ctx.defer()
        
    # Connect to the voice channel if not already connected
    vc = ctx.voice_client
    try:
        if not vc:
            vc = await ctx.author.voice.channel.connect()
            
        if vc.recording:
            await ctx.respond("⚠️ Already recording in this voice channel.")
            return
            
        # Store the session start time
        recording_sessions[ctx.guild.id] = (vc, time.time())
        
        # Start recording (Using WaveSink as it's the most stable format)
        vc.start_recording(
            discord.sinks.WaveSink(),
            once_done,
            ctx.channel
        )
        
        # Send a response explaining recording has started and notifying users (privacy)
        await ctx.respond(
            "🎙️ **Started recording!**\n"
            "⚠️ *Disclaimer: By remaining in this voice channel, you consent to being recorded and transcribed. "
            "The transcript and audio will be posted in this chat channel when the recording is stopped.*"
        )
    except Exception as e:
        traceback.print_exc()
        await ctx.respond(f"❌ Failed to start recording: {e}")

@bot.slash_command(name="stop", description="Stop recording, save audio, and generate transcript.")
async def stop(ctx: discord.ApplicationContext):
    vc = ctx.voice_client
    if not vc or not vc.recording:
        await ctx.respond("❌ The bot is not currently recording in this server.")
        return
        
    # Defer interaction immediately to prevent timeout
    await ctx.defer()
    await ctx.respond("⏳ Stopping the recording and beginning audio transcription. Please wait...")
    vc.stop_recording()

@bot.slash_command(name="leave", description="Disconnect the bot from the voice channel.")
async def leave(ctx: discord.ApplicationContext):
    vc = ctx.voice_client
    if not vc:
        await ctx.respond("❌ The bot is not connected to a voice channel.")
        return
        
    # Defer interaction immediately to prevent timeout
    await ctx.defer()
    
    # Stop recording first if active
    if vc.recording:
        vc.stop_recording()
        
    try:
        await vc.disconnect()
        await ctx.respond("🚪 Disconnected from the voice channel.")
    except Exception as e:
        traceback.print_exc()
        await ctx.respond(f"❌ Failed to disconnect: {e}")

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        bot.run(config.DISCORD_TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN is missing. Cannot start bot.")
