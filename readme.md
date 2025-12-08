# 🍭 Candy Panel - WireGuard Management System

A modern, beautiful web interface for managing WireGuard VPN servers with comprehensive backend integration. Built with React, TypeScript, and a powerful Python Flask backend.

![Candy Panel Dashboard](https://github.com/AmiRCandy/Candy-Panel/blob/15d1fa6852bb187ccbfcc5712c481cc3d00235cc/image.png)

## ✨ Features

- 🎨 **Beautiful UI**: Modern glassmorphism design with smooth animations
- 🔐 **Secure Authentication**: JWT-based authentication system
- 👥 **Client Management**: Create, edit, delete, and monitor WireGuard clients
- 🖥️ **Server Control**: Comprehensive WireGuard server management
- ⚙️ **Interface Configuration**: Manage multiple WireGuard interfaces (wg0, wg1, etc.)
- 📊 **Real-time Statistics**: Live bandwidth monitoring and analytics
- 🔑 **API Management**: Generate and manage API tokens
- ⏰ **Auto Reset**: Scheduled server resets with configurable intervals
- 🛠️ **Installation Wizard**: Guided setup for first-time users
- 📱 **Responsive Design**: Works perfectly on desktop, tablet, and mobile

## 🚀 Quick Start

### 🚀 One line command install

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/AmiRCandy/Candy-Panel/main/setup.sh)"
```
- Panel Default Port : 3446
- API Default Port : 3446

### Prerequisites

- Node.js 20+ and npm
- Python 3.8+
- WireGuard installed on your server

### Frontend Setup

1. **Clone the repository**
```bash
git clone https://github.com/AmiRCandy/Candy-Panel.git
cd candy-panel
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment**
```bash
cp .env.example .env
```

4. **Start development server**
```bash
npm run dev
```

### Backend Setup

1. **Navigate to backend directory**
```bash
cd backend
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Start the backend server**
```bash
python main.py
```

4. **Access the application**
   - Frontend: `http://localhost:3446`
   - Backend API: `http://localhost:3446`

## 🏗️ Architecture

### Frontend Stack
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **React Router** for navigation

### Backend Stack
- **Flask** for high-performance API
- **SQLite** for database management
- **WireGuard** integration for VPN management

## 🔧 Configuration

### Environment Variables

For installing Telegram BOT you must enter your api_id , api_hash , so put them in var and export on env:

```env
export TELEGRAM_API_ID=1
export TELEGRAM_API_HASH=ab12
```

### Backend Configuration

The backend automatically creates a SQLite database and initializes default settings on first run.

## 🎯 Usage

### First Time Setup

1. **Access the application** at `http://localhost:3446`
2. **Run the installation wizard** to configure your server
3. **Set up admin credentials** and server settings
4. **Create your first WireGuard interface**
5. **Add clients** and start managing your VPN

### Managing Clients

1. Navigate to the **Clients** page
2. Click **"Add Client"** to create a new VPN user
3. Configure traffic limits, expiration dates, and notes
4. Download the configuration file or share it with users
5. Monitor client usage and connection status in real-time

### Server Configuration

1. Go to the **Settings** page to configure global settings
2. Set DNS servers, MTU values, and reset schedules
3. Enable/disable auto-backup functionality
4. Monitor server statistics and performance

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Row Level Security**: Database-level access control
- **API Token Management**: Granular API access control
- **Auto Session Timeout**: Configurable session management
- **Secure Key Generation**: Cryptographically secure WireGuard keys

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [WireGuard](https://www.wireguard.com/) for the amazing VPN technology
- [shadcn/ui](https://ui.shadcn.com/) for the beautiful UI components
- [React](https://reactjs.org/) and [Vite](https://vitejs.dev/) for the frontend tools (Frontend built by [BoltAI](https://bolt.new))

## 📞 Support

- 📧 Email: amirhosen.1385.cmo@gmail.com
- 💬 Discord: [Join our community](https://discord.gg/candypanel)
- 🐛 Issues: [GitHub Issues](https://github.com/AmiRCandy/Candy-Panel/issues)
- 📖 Documentation: [Wiki](https://github.com/AmiRCandy/Candy-Panel)
- 📖 X (Twiiter): [AmiR](https://x.com/BeNamKhodaHastm)

## 🗺️ Roadmap

- [x] Telegram bot integration for automated sales
- [x] IPV6 Support
- [ ] Advanced analytics and reporting
- [ ] Docker containerization
- [x] Manual Port for panel and api
- [ ] Automatic tunnel installation
- [ ] Theme customization

---
## Credits

Thanks to [@Byte-Aura](https://github.com/Byte-Aura) for help with planning and testing.



<div align="center">
  <p>Built with 💜 for WireGuard Enthusiasts</p>
  <p>
    <a href="https://github.com/AmiRCandy/Candy-Panel/stargazers">⭐ Star us on GitHub</a> •
    <a href="https://github.com/AmiRCandy/Candy-Panel/issues">🐛 Report Bug</a> •
    <a href="https://github.com/AmiRCandy/Candy-Panel/issues">✨ Request Feature</a>
  </p>
</div>
