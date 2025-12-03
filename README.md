# 🌤️ City Weather Poster - Automated Social Media Bot

Automatically generate beautiful isometric 3D city weather images using Google's Nano Banana (Gemini 2.5 Flash Image) and post them to Instagram, X (Twitter), and TikTok.

## 🎯 Features

- **Dynamic City Configuration**: Easy YAML config for multiple cities/accounts
- **Timezone-Aware Posting**: Posts at optimal times based on each city's timezone
- **Multi-Platform Support**: Instagram, X (Twitter), TikTok
- **Real Weather Data**: Fetches current weather from OpenWeatherMap
- **Beautiful AI Images**: Uses Google's Nano Banana for stunning isometric city scenes
- **GitHub Actions Powered**: Free automated scheduling

## 📁 Project Structure

```
city-weather-poster/
├── .github/
│   └── workflows/
│       └── post-weather.yml    # GitHub Actions scheduler
├── src/
│   ├── __init__.py
│   ├── config.py               # Configuration loader
│   ├── weather.py              # OpenWeatherMap integration
│   ├── image_generator.py      # Nano Banana (Gemini) integration
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── instagram.py        # Instagram Graph API
│   │   ├── twitter.py          # X API v2
│   │   └── tiktok.py           # TikTok API
│   └── main.py                 # Main orchestration
├── config/
│   └── cities.yaml             # City configurations
├── requirements.txt
└── README.md
```

## 🚀 Quick Setup

### 1. Fork & Clone this Repository

```bash
git clone https://github.com/YOUR_USERNAME/city-weather-poster.git
cd city-weather-poster
```

### 2. Get Your API Keys

#### Google AI (Nano Banana / Gemini)
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API Key" → Create API key
3. Save your API key

#### OpenWeatherMap
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Go to API keys section
3. Copy your API key (free tier: 1000 calls/day)

#### X (Twitter) API
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new App (Free tier allows posting)
3. Generate: API Key, API Secret, Access Token, Access Token Secret

#### Instagram Graph API
1. Create a [Meta Business Account](https://business.facebook.com/)
2. Convert your Instagram to a Business/Creator account
3. Create an app at [Meta Developers](https://developers.facebook.com/)
4. Add Instagram Graph API product
5. Generate a long-lived access token
6. Get your Instagram Business Account ID

#### TikTok API
1. Go to [TikTok for Developers](https://developers.tiktok.com/)
2. Create an app and request Video Publishing permissions
3. Complete app review process
4. Get Client Key and Client Secret

### 3. Configure GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

```
GOOGLE_AI_API_KEY=your_google_ai_key
OPENWEATHER_API_KEY=your_openweather_key

# For each city account (example for Tokyo):
TOKYO_TWITTER_API_KEY=xxx
TOKYO_TWITTER_API_SECRET=xxx
TOKYO_TWITTER_ACCESS_TOKEN=xxx
TOKYO_TWITTER_ACCESS_TOKEN_SECRET=xxx
TOKYO_INSTAGRAM_ACCESS_TOKEN=xxx
TOKYO_INSTAGRAM_ACCOUNT_ID=xxx
TOKYO_TIKTOK_ACCESS_TOKEN=xxx
```

### 4. Configure Your Cities

Edit `config/cities.yaml`:

```yaml
cities:
  tokyo:
    name: "Tokyo"
    country: "Japan"
    timezone: "Asia/Tokyo"
    coordinates:
      lat: 35.6762
      lon: 139.6503
    posting_times:
      - "08:00"  # Morning post
      - "18:00"  # Evening post
    platforms:
      twitter: true
      instagram: true
      tiktok: true
    landmarks: "Tokyo Tower, Shibuya Crossing, Mount Fuji in background, cherry blossoms"
```

### 5. Enable GitHub Actions

1. Go to your repo → Actions tab
2. Click "I understand my workflows, go ahead and enable them"
3. The bot will run automatically based on your schedule!

## ⚙️ Configuration Options

### cities.yaml Structure

| Field | Description | Example |
|-------|-------------|---------|
| `name` | City display name | "New York" |
| `country` | Country name | "USA" |
| `timezone` | IANA timezone | "America/New_York" |
| `coordinates` | Lat/Lon for weather | `{lat: 40.7128, lon: -74.0060}` |
| `posting_times` | Local times to post | `["08:00", "20:00"]` |
| `platforms` | Which platforms to post to | `{twitter: true, instagram: true}` |
| `landmarks` | City-specific landmarks for prompt | "Statue of Liberty, Empire State..." |

### Adding a New City

1. Add entry to `cities.yaml`
2. Add corresponding secrets to GitHub
3. That's it! Next scheduled run will include the new city.

## 🔧 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_AI_API_KEY="your_key"
export OPENWEATHER_API_KEY="your_key"
# ... other keys

# Run manually
python -m src.main --city tokyo --dry-run
```

## 📊 Monitoring

- Check GitHub Actions tab for run history
- Each run logs: weather data, image generation status, posting results
- Failed posts are logged with error details

## 💰 Cost Estimation

| Service | Cost | Notes |
|---------|------|-------|
| Nano Banana | ~$0.04/image | 1290 tokens × $30/1M tokens |
| OpenWeatherMap | Free | 1000 calls/day free tier |
| GitHub Actions | Free | 2000 min/month for public repos |
| X API | Free | Free tier allows posting |
| Instagram | Free | Via Graph API |
| TikTok | Free | Via official API |

**Example**: 5 cities × 2 posts/day = 10 images/day = ~$0.40/day = ~$12/month

## 🐛 Troubleshooting

### Image Generation Fails
- Check Google AI API quota
- Verify API key is correct
- Check prompt isn't triggering content filters

### Posting Fails
- Verify access tokens haven't expired
- Check platform rate limits
- Instagram requires business account

### Weather Data Missing
- Verify city coordinates are correct
- Check OpenWeatherMap API key

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

PRs welcome! Please open an issue first to discuss changes.
