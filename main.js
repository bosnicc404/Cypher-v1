const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

function createWindow() {
    const win = new BrowserWindow({
        width: 1280,
        height: 800,
        title: "CYPHER SYSTEM v1.0",
        backgroundColor: '#0a0a0a',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            webSecurity: false
        }
    });

    win.setMenuBarVisibility(false);
    win.loadFile('index.html');
}

app.whenReady().then(() => {
    const bridgePath = path.join(__dirname, 'bridge.py');

    const pyProcess = spawn('python', [bridgePath], {
        cwd: __dirname,
        stdio: 'inherit'
    });

    pyProcess.on('error', (err) => {
        console.error("Failed to start bridge.py!", err);
    });

    setTimeout(createWindow, 7000);
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
