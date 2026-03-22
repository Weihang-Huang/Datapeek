/**
 * DataPeek preload — minimal, expose nothing unless needed.
 */
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('datapeek', {
    platform: process.platform,
});
