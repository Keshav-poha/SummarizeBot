const fs = require('fs');
const path = require('path');
const os = require('os');
const { joinVoiceChannel, EndBehaviorType, getVoiceConnection, createAudioPlayer, NoSubscriberBehavior, createAudioResource } = require('@discordjs/voice');
const { exec } = require('child_process');
const prism = require('prism-media');

const recordingSessions = new Map();

const createNewChunk = (userId) => {
    const tempFilePath = path.join(os.tmpdir(), `rec_${userId}_${Date.now()}.pcm`);
    return { writeStream: fs.createWriteStream(tempFilePath), tempFilePath };
};

exports.enter = async function(msg, client) {
    const voiceChannel = msg.member?.voice.channel;
    
    if (!voiceChannel)
        return msg.reply('❌ You need to join a voice channel first!');
    
    console.log(`Sliding into ${voiceChannel.name} ...`);
    
    const connection = joinVoiceChannel({
        channelId: voiceChannel.id,
        guildId: voiceChannel.guild.id,
        adapterCreator: voiceChannel.guild.voiceAdapterCreator,
        selfDeaf: false,
        debug: true
    });

    connection.on('stateChange', (oldState, newState) => {
        console.log(`Connection transitioned from ${oldState.status} to ${newState.status}`);
    });
    
    connection.on('error', (error) => {
        console.error('Voice Connection Error:', error);
    });

    recordingSessions.set(voiceChannel.guild.id, {
        channel: msg.channel,
        userStreams: new Map(),
        startTime: Date.now()
    });

    // Play a tiny bit of silence to kickstart the UDP connection
    const player = createAudioPlayer({
        behaviors: { noSubscriber: NoSubscriberBehavior.Play }
    });
    const silencePath = path.join(__dirname, '..', 'sounds', 'drop.mp3');
    // If the file doesn't exist, we fallback to a silent Ogg or similar, but the user's repo had sounds/drop.mp3
    if (fs.existsSync(silencePath)) {
        player.play(createAudioResource(silencePath));
        connection.subscribe(player);
    }

    connection.receiver.speaking.on('start', (userId) => {
        const session = recordingSessions.get(voiceChannel.guild.id);
        if (!session) return;
        
        if (!session.userStreams.has(userId)) {
            const opusStream = connection.receiver.subscribe(userId, {
                end: {
                    behavior: EndBehaviorType.Manual,
                },
            });

            const pcmStream = new prism.opus.Decoder({
                rate: 48000,
                channels: 2,
                frameSize: 960,
            });

            const { writeStream, tempFilePath } = createNewChunk(userId);
            opusStream.pipe(pcmStream).pipe(writeStream);

            session.userStreams.set(userId, { tempFilePath, opusStream, writeStream });
            console.log(`Started recording user ${userId}`);
        }
    });

    await msg.reply('🎙️ **Started recording!** (DAVE E2EE Bypass Active)\nType `!stop` to finish and summarize.');
}

exports.exit = function (msg, client) {
    const voiceChannel = msg.member?.voice.channel;
    if (!voiceChannel) {
        return msg.reply('❌ You are not in a voice channel!');
    }

    const connection = getVoiceConnection(voiceChannel.guild.id);
    if (!connection) {
        return msg.reply('❌ Bot is not in a voice channel.');
    }

    const session = recordingSessions.get(voiceChannel.guild.id);
    if (!session) {
        return msg.reply('❌ No recording session found.');
    }

    const duration = Math.floor((Date.now() - session.startTime) / 1000);
    msg.reply(`⏳ **Recording stopped!** (${duration}s)\nProcessing audio and generating summary...`);

    connection.destroy();
    recordingSessions.delete(voiceChannel.guild.id);

    const userFiles = [];
    for (const [userId, streamData] of session.userStreams.entries()) {
        userFiles.push(streamData.tempFilePath);
        streamData.opusStream.destroy();
        streamData.writeStream.end();
    }

    if (userFiles.length === 0) {
        return session.channel.send('⚠️ No audio was captured (nobody spoke).');
    }

    // Give Node.js a second to completely flush the PCM streams to the hard drive
    setTimeout(() => {
        const outWav = path.join(os.tmpdir(), `merged_${Date.now()}.wav`);
        
        let ffmpegCmd = `ffmpeg -y `;
        userFiles.forEach(f => {
            ffmpegCmd += `-f s16le -ar 48000 -ac 2 -i "${f}" `;
        });

    if (files.length > 1) {
        ffmpegCmd += `-filter_complex amix=inputs=${files.length}:duration=longest `;
    }
    
    ffmpegCmd += `"${outWav}"`;

        exec(ffmpegCmd, (error) => {
            // Delete raw PCM files
            userFiles.forEach(f => {
                try { fs.unlinkSync(f); } catch (e) {}
            });

        if (error) {
            console.error("FFmpeg error:", error);
            return session.channel.send('❌ Failed to merge audio files.');
        }

        session.channel.send('🎙️ Audio merged. Running local Whisper transcription and Ollama summarization...');
        
        const pythonScript = path.join(process.cwd(), 'transcriber.py');
        
        let pythonCmd = os.platform() === 'win32' ? 'python' : 'python3';
        const venvWin = path.join(process.cwd(), 'venv', 'Scripts', 'python.exe');
        const venvLin = path.join(process.cwd(), 'venv', 'bin', 'python');
        
        if (fs.existsSync(venvWin)) {
            pythonCmd = `"${venvWin}"`;
        } else if (fs.existsSync(venvLin)) {
            pythonCmd = `"${venvLin}"`;
        }
        
        exec(`${pythonCmd} "${pythonScript}" "${outWav}"`, (pyErr, stdout, stderr) => {
            try { fs.unlinkSync(outWav); } catch(e) {}
            
            if (stderr) console.error("Python Stderr:", stderr);
            
            if (pyErr) {
                console.error("Python Error:", pyErr);
                return session.channel.send('❌ Failed to transcribe or summarize audio.');
            }

            try {
                const result = JSON.parse(stdout.trim());
                if (result.error) {
                    return session.channel.send(`❌ Summarization error: ${result.error}`);
                }
                
                const reply = `📝 **Meeting Summary:**\n> ${result.summary.replace(/\\n/g, '\n> ')}\n\n*Full Transcript attached below.*`;
                
                const txPath = path.join(os.tmpdir(), `transcript_${Date.now()}.txt`);
                fs.writeFileSync(txPath, result.transcript);
                session.channel.send({
                    content: reply,
                    files: [txPath]
                }).then(() => {
                    fs.unlinkSync(txPath);
                }).catch(console.error);

            } catch (parseErr) {
                console.error("Failed to parse JSON:", stdout);
                session.channel.send('❌ Failed to parse summarization result.');
            }
        });
    });
    }, 1000); // 1 second timeout
};