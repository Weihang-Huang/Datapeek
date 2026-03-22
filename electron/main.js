/**
 * DataPeek Electron shell — spawns Flask backend and opens a BrowserWindow.
 */
const { app, BrowserWindow, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let flaskProcess = null;
const PORT = 5000;
const FLASK_URL = `http://127.0.0.1:${PORT}`;

function getServerPath() {
    // In packaged app, look in resources; in dev, use python directly
    if (app.isPackaged) {
        const ext = process.platform === 'win32' ? '.exe' : '';
        return path.join(process.resourcesPath, 'datapeek-server' + ext);
    }
    return null; // dev mode — start via Python
}

function startFlask() {
    const serverPath = getServerPath();
    if (serverPath) {
        flaskProcess = spawn(serverPath, [], { stdio: 'pipe' });
    } else {
        // Development mode: run Flask via Python
        const appPath = path.join(__dirname, '..', 'web_app', 'app.py');
        flaskProcess = spawn('python', [appPath], {
            cwd: path.join(__dirname, '..'),
            stdio: 'pipe',
            env: { ...process.env, FLASK_ENV: 'production' },
        });
    }

    flaskProcess.stdout.on('data', (data) => console.log(`[Flask] ${data}`));
    flaskProcess.stderr.on('data', (data) => console.error(`[Flask] ${data}`));
    flaskProcess.on('close', (code) => console.log(`Flask exited with code ${code}`));
}

function waitForFlask(retries = 30) {
    return new Promise((resolve, reject) => {
        function check(n) {
            if (n <= 0) return reject(new Error('Flask did not start'));
            http.get(FLASK_URL, (res) => {
                resolve();
            }).on('error', () => {
                setTimeout(() => check(n - 1), 500);
            });
        }
        check(retries);
    });
}

async function createWindow() {
    startFlask();
    await waitForFlask();

    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        title: 'DataPeek',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    Menu.setApplicationMenu(null);
    mainWindow.loadURL(FLASK_URL);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (flaskProcess) {
        flaskProcess.kill();
        flaskProcess = null;
    }
    app.quit();
});

app.on('before-quit', () => {
    if (flaskProcess) {
        flaskProcess.kill();
        flaskProcess = null;
    }
});
