/**
 * Electron Preload Script
 *
 * Exposes a secure API to the renderer via contextBridge.
 * Only approved async methods are exposed — no direct Node.js access.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  /**
   * Run content analysis on text.
   * @param {string} text - Content to analyze
   * @returns {Promise<object>} - { success, data: { violations, summary } }
   */
  analyze: (text) => ipcRenderer.invoke('analyze', text),

  /**
   * Rewrite text using rule engine.
   * @param {string} text - Content to rewrite
   * @returns {Promise<object>} - { success, data: { rewritten, changes, sentenceWarnings } }
   */
  rewrite: (text) => ipcRenderer.invoke('rewrite', text),

  /**
   * Convert text to DITA XML.
   * @param {string} text - Content to convert
   * @param {string} format - "concept" or "task"
   * @returns {Promise<object>} - { success, data: { xml } }
   */
  convertDita: (text, format) => ipcRenderer.invoke('convert-dita', text, format),

  /**
   * Run impact analysis comparing JIRA items to DITA topics.
   * @param {Array} jiraItems - Parsed JIRA items
   * @param {Array} ditaTopics - Parsed DITA topics
   * @param {number} threshold - Similarity threshold
   * @returns {Promise<object>} - { success, data: { topicsToCreate, topicsToUpdate } }
   */
  impactAnalyze: (jiraItems, ditaTopics, threshold) =>
    ipcRenderer.invoke('impact-analyze', jiraItems, ditaTopics, threshold),

  /**
   * Listen for backend error events.
   * @param {function} callback - Called with error info
   */
  onBackendError: (callback) => {
    ipcRenderer.on('backend-error', (event, data) => callback(data));
  },

  /**
   * Listen for backend ready event.
   * @param {function} callback - Called when backend is ready
   */
  onBackendReady: (callback) => {
    ipcRenderer.on('backend-ready', (event) => callback());
  },

  /**
   * Poll backend status (fallback for race conditions).
   * @returns {Promise<object>} - { ready: boolean }
   */
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
});
