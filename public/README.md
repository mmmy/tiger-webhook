# Static Files and Templates

This directory contains the static files and HTML templates for the Deribit Webhook Python dashboard.

## Structure

```
public/
├── index.html              # Main dashboard HTML
├── static/
│   ├── css/
│   │   └── dashboard.css   # Dashboard styles
│   ├── js/
│   │   └── dashboard.js    # Dashboard JavaScript
│   └── favicon.ico         # Favicon (placeholder)
└── README.md              # This file
```

## Dashboard Features

The dashboard provides a web interface for monitoring and controlling the Deribit Webhook service:

### Service Status
- Real-time service health monitoring
- Version and environment information
- Mock mode indicator

### Account Management
- List of enabled accounts
- Account status indicators

### Position Polling
- Polling status display
- Start/stop polling controls
- Manual poll trigger

### WeChat Bot Integration
- Number of configured bots
- Test all bots functionality

### API Endpoints
- Quick reference to available endpoints
- Direct links to API documentation

### Activity Logs
- Real-time activity logging
- Error and success notifications
- Automatic log rotation

## Usage

The dashboard is automatically served at the root URL (`/`) when the FastAPI application is running.

### API Integration

The dashboard communicates with the backend through REST API calls:

- `GET /api/status` - Service status
- `GET /api/positions/polling/status` - Polling status
- `POST /api/positions/polling/start` - Start polling
- `POST /api/positions/polling/stop` - Stop polling
- `POST /api/positions/poll` - Manual poll
- `GET /api/wechat/configs` - WeChat configurations
- `POST /api/wechat/test-all` - Test all WeChat bots

### Auto-refresh

The dashboard automatically refreshes data every 30 seconds to provide real-time updates.

## Customization

### Styling
Modify `static/css/dashboard.css` to customize the appearance.

### Functionality
Extend `static/js/dashboard.js` to add new features or modify existing behavior.

### Layout
Update `index.html` to change the dashboard layout or add new sections.

## Production Considerations

1. **Security**: Configure CORS appropriately for production environments
2. **Caching**: Add appropriate cache headers for static assets
3. **Compression**: Enable gzip compression for better performance
4. **CDN**: Consider using a CDN for static asset delivery
5. **Favicon**: Replace the placeholder favicon with a proper ICO file

## Browser Compatibility

The dashboard is designed to work with modern browsers that support:
- ES6+ JavaScript features
- CSS Grid and Flexbox
- Fetch API
- Modern CSS features

## Development

To modify the dashboard during development:

1. Edit the HTML, CSS, or JavaScript files
2. Refresh the browser to see changes
3. Use browser developer tools for debugging
4. Test API endpoints using the browser's network tab

The dashboard uses vanilla JavaScript (no frameworks) for simplicity and minimal dependencies.
