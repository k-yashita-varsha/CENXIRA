const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// Middleware
app.use(express.static(path.join(__dirname)));

// API endpoint to serve correct dashboard based on role
app.get('/api/get-dashboard', (req, res) => {
    const token = req.query.token;
    const role = req.query.role;

    if (!token || !role) {
        return res.status(400).json({ error: 'Token and role required' });
    }

    // Map roles to HTML files
    const dashboardMap = {
        'Admin': 'admin.html',
        'Manager': 'manager.html',
        'Trainee': 'trainee.html'
    };

    const dashboardFile = dashboardMap[role];

    if (!dashboardFile) {
        return res.status(404).json({ error: 'Invalid role' });
    }

    const filePath = path.join(__dirname, dashboardFile);

    // Check if file exists
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: `Dashboard file not found: ${dashboardFile}` });
    }

    res.sendFile(filePath);
});

// Serve index.html for root and login
app.get(['/', '/index.html'], (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Serve admin.html
app.get('/admin.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'admin.html'));
});

// Serve manager.html
app.get('/manager.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'manager.html'));
});

// Serve trainee.html
app.get('/trainee.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'trainee.html'));
});

// 404 handler
app.use((req, res) => {
    res.status(404).sendFile(path.join(__dirname, 'index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log(`╔════════════════════════════════════════════════════════════╗`);
    console.log(`║                                                            ║`);
    console.log(`║        ✅ Training Portal Running Successfully! ✅        ║`);
    console.log(`║                                                            ║`);
    console.log(`╚════════════════════════════════════════════════════════════╝`);
    console.log(`🌐 Open your browser and go to: http://localhost:${PORT}`);
    console.log(`Make sure backend is running: cd training_portal && python main.py`);
});