const { Client, GatewayIntentBits } = require('discord.js');
const dotenv = require('dotenv');
const commands = require(`./bin/commands`);

dotenv.config();

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

if(!process.env.DISCORD_TOKEN) {
    console.error("Error: DISCORD_TOKEN is not set in the environment variables.");
    process.exit(1);
}

const PREFIX = process.env.PREFIX || '!';

client.on('messageCreate', msg => {
    if (msg.author.bot) return;

    if (msg.content.startsWith(PREFIX)) {
        const commandBody = msg.content.substring(PREFIX.length).split(' ');
        
        if (commandBody[0] === 'record') commands.enter(msg, client);
        if (commandBody[0] === 'stop') commands.exit(msg, client);
    }
});

client.once('clientReady', () => {
    console.log(`\nONLINE - Logged in as ${client.user.tag}\n`);
    console.log(`Requires @snazzah/davey installed for DAVE E2EE support.`);
});

client.login(process.env.DISCORD_TOKEN);
