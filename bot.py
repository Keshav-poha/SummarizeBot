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
intents.voice_states = True
intents.guilds = True
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

def format_error(e: Exception) -> str:
    """Formats exceptions nicely even when str(e) is empty (e.g. asyncio.TimeoutError)."""
    err_str = str(e).strip()
    err_type = type(e).__name__
    if not err_str:
        if isinstance(e, asyncio.TimeoutError):
            return f"{err_type}: Connection timed out waiting for Discord voice server. Make sure 'Voice States' intent is enabled in Developer Portal and the bot has 'Connect' & 'Speak' permissions."
        return f"{err_type}: Connection failed."
    return f"{err_type}: {err_str}"

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user} (ID: {bot.user.id})")
    
    # Ensure PyNaCl is loaded for voice encryption
    try:
        import nacl.secret
        print("🔐 PyNaCl voice encryption library loaded successfully.")
    except Exception as e:
        print(f"❌ Error: PyNaCl library failed to load: {e}")
    
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

class DebugVoiceClient(discord.VoiceClient):
    """Custom VoiceClient subclass that guarantees valid endpoints and cleans :8443 suffixes."""
    async def disconnect(self, *, force: bool = False) -> None:
        print(f"⚠️ DebugVoiceClient: disconnect() triggered (force={force})!", flush=True)
        await super().disconnect(force=force)

    async def connect_websocket(self):
        """Ensures endpoint is valid before attempting websocket connection."""
        print(f"🔌 DebugVoiceClient: preparing websocket for endpoint='{getattr(self, 'endpoint', None)}'", flush=True)
        # Wait up to 5s for endpoint to be populated by gateway
        for _ in range(50):
            if hasattr(self, 'endpoint') and self.endpoint and isinstance(self.endpoint, str) and self.endpoint.strip():
                break
            await asyncio.sleep(0.1)

        if not hasattr(self, 'endpoint') or not self.endpoint or not isinstance(self.endpoint, str) or not self.endpoint.strip():
            print("❌ DebugVoiceClient error: Discord Gateway did not provide a voice server endpoint.", flush=True)
            raise asyncio.TimeoutError("Voice server endpoint was not provided by Discord Gateway.")

        self.endpoint = self.endpoint.replace(':8443', '').strip()
        print(f"🌐 Connecting to voice websocket at: wss://{self.endpoint}/?v=4", flush=True)
        return await super().connect_websocket()

    async def on_voice_state_update(self, data) -> None:
        print(f"🔊 DebugVoiceClient: voice_state_update payload: {data}")
        await super().on_voice_state_update(data)

    async def on_voice_server_update(self, data) -> None:
        print(f"🔊 DebugVoiceClient: raw voice_server_update payload: {data}")
        if data and isinstance(data, dict):
            ep = data.get('endpoint')
            if ep and isinstance(ep, str) and ep.strip():
                clean_ep = ep.replace(':8443', '').strip()
                data['endpoint'] = clean_ep
                print(f"🔧 Cleaned voice_server_update endpoint: '{ep}' -> '{clean_ep}'")
        await super().on_voice_server_update(data)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Logs when the bot joins or disconnects from voice channels."""
    if member.id == bot.user.id:
        if before.channel is not None and after.channel is None:
            print(f"⚠️ Bot disconnected from voice channel '{before.channel.name}' (Guild: {before.channel.guild.name})")
        elif before.channel is None and after.channel is not None:
            print(f"🔊 Bot joined voice channel '{after.channel.name}' (Guild: {after.channel.guild.name})")
        elif before.channel != after.channel:
            print(f"🔀 Bot moved from '{before.channel.name}' to '{after.channel.name}'")

@bot.event
async def on_error(event_method: str, *args, **kwargs):
    """Logs detailed tracebacks for unhandled events."""
    print(f"❌ Exception in event handler '{event_method}':")
    traceback.print_exc()

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
            try:
                await ctx.voice_client.disconnect(force=True)
            except Exception:
                pass
        
        # Clear any stale/ghost voice connections from previous crashes or restarts
        try:
            await ctx.guild.change_voice_state(channel=None)
            await asyncio.sleep(0.5)
        except Exception:
            pass
            
        print(f"🔄 Attempting to connect to voice channel: {channel.name} (Guild: {channel.guild.name})...")
        vc = await channel.connect(cls=DebugVoiceClient, timeout=60.0, reconnect=True)
        print(f"✅ Connected to voice channel {channel.name} successfully!")
        await ctx.respond(f"✅ Joined **{channel.name}**")
    except Exception as e:
        print(f"❌ Exception during voice connection to {channel.name}:")
        traceback.print_exc()
        await ctx.respond(f"❌ Failed to join voice channel: {format_error(e)}")

@bot.slash_command(name="record", description="Start recording the voice channel.")
async def record(ctx: discord.ApplicationContext):
    if not ctx.author.voice:
        await ctx.respond("❌ You must be in a voice channel to start recording!")
        return
        
    # Defer interaction to prevent Discord 3-second timeout
    await ctx.defer()
        
    channel = ctx.author.voice.channel
    vc = ctx.voice_client
    
    # If a voice client exists but is not connected, clean it up
    if vc and not vc.is_connected():
        try:
            await vc.disconnect(force=True)
        except Exception:
            pass
        vc = None
        
    try:
        if not vc:
            # Clear any stale/ghost voice state before connecting
            try:
                await ctx.guild.change_voice_state(channel=None)
                await asyncio.sleep(0.5)
            except Exception:
                pass
            print(f"🔄 Attempting voice connection for recording: {channel.name}...")
            vc = await channel.connect(cls=DebugVoiceClient, timeout=60.0, reconnect=True)
            print(f"✅ Voice connected for recording: {channel.name}")
            
        if not vc or not vc.is_connected():
            await ctx.respond("❌ Could not establish a voice connection to the channel.")
            return

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
        await ctx.respond(f"❌ Failed to start recording: {format_error(e)}")

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
    # Defer interaction immediately to prevent timeout
    await ctx.defer()

    vc = ctx.voice_client
    if vc:
        if vc.recording:
            vc.stop_recording()
        try:
            await vc.disconnect(force=True)
        except Exception:
            pass
        
    try:
        await ctx.guild.change_voice_state(channel=None)
        await ctx.respond("🚪 Disconnected from the voice channel.")
    except Exception as e:
        traceback.print_exc()
        await ctx.respond(f"❌ Failed to disconnect: {format_error(e)}")

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        bot.run(config.DISCORD_TOKEN)
    else:
        print("❌ Error: DISCORD_TOKEN is missing. Cannot start bot.")
