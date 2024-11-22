# MyMusic User Manual

I created YoutubeMusic to help you export music playlists, organize them efficiently, and enjoy them through a web app with both video and audio playback capabilities. I want to thank the resources that made this project possible, including [Claude.ai](https://claude.ai), [GitHub](https://github.com), [GitHub Pages](https://pages.github.com), [OnRender.com](https://onrender.com), and [SoundCloud](https://soundcloud.com).

## Step 1: Exporting Your Spotify Playlist to CSV

### 1. Preparing Your Playlist
First, open your [Spotify](https://open.spotify.com) account and select the playlists you want to export.

### 2. Using TuneMyMusic
I used [TuneMyMusic](https://tunemymusic.com) for the export process:
- Go to TuneMyMusic's website
- Select Spotify as your source
- Follow their export instructions to get your playlist in CSV format

The exported CSV includes important song details:
- Title
- Artist Name
- Album Name
- Playlist Name
- Type
- ISRC Code
- Spotify ID

### 3. Cleaning Up the CSV Data
I found that not all exported data was necessary, so I:
- Removed unnecessary columns (Playlist Name, Type, ISRC, Spotify ID)
- Kept only the essential columns: Song Title, Artist Name, and Album Name
- After cleaning, my final list contained 2,965 songs

## Step 2: Extracting Media Links

### 1. Web Scraping Process
I developed a Python script that:
- Automatically searches YouTube using the Song Title and Album Name
- Uses web scraping to extract YouTube video links
- Searches SoundCloud through web scraping to find audio versions
- Collects SoundCloud track URLs when available
- Enables both video and audio playback functionality in the app

### 2. SoundCloud Integration
I implemented SoundCloud support through web scraping to avoid API costs:
- Scraping track information directly from SoundCloud's website
- Storing direct track URLs for each song when available
- Creating fallback options when songs aren't found
- Implementing embedded players using the free widget option

## Step 3: Creating the Web App

### 1. Web App Development
I built the app with these features:
- Video playback using YouTube embeds
- Audio playback through SoundCloud embeds
- Toggle between video and audio modes
- Embedded SoundCloud player featuring:
  - Play/pause controls
  - Volume adjustment
  - Progress bar
  - Playlist navigation
- Clean and intuitive user interface
- Responsive design for mobile and desktop

### 2. Deployment
I made the app accessible by:
- Hosting the code on GitHub
- Deploying the live version using GitHub Pages and OnRender.com
- Ensuring browser-based access for all users
- Testing cross-platform compatibility

## Try It Out
You can access the live version of MyMusic here: [MyMusic Web App](https://mymusic-793b.onrender.com)

## Source Code
Check out the project source code: [GitHub Repository](https://github.com/VazeerAhmed/MyMusic)

## Special Thanks

This project wouldn't have been possible without:
- [Claude.ai](https://claude.ai) - For AI assistance and guidance
- [GitHub](https://github.com) - For reliable code hosting
- [OnRender.com](https://onrender.com) - For seamless web deployment
- [SoundCloud](https://soundcloud.com) - For audio content integration
- [YouTube](https://youtube.com) - For video content integration

## Note on Copyright and Use
This project uses web scraping techniques instead of APIs to keep it cost-effective and accessible. All content is played through official embedded players from YouTube and SoundCloud. All rights to the media content are reserved by the respective platforms and copyright owners.
