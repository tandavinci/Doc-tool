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
   * Convert a file or URL to Markdown using MarkItDown.
   * @param {object} payload - { mode: 'file'|'url', filename, fileData, url }
   * @returns {Promise<object>} - { success, data: { markdown, filename } }
   */
  markitdownConvert: (payload) => ipcRenderer.invoke('markitdown-convert', payload),

  /**
   * Run quick documentation compliance review.
   * @param {string} text - Content to review
   * @returns {Promise<object>} - { success, data: { classification, score, violations, suggestions, rewritten, rewrite_changes, ... } }
   */
  quickReview: (text) => ipcRenderer.invoke('quick-review', text),

  /**
   * Send a chat message to the AI Assistant.
   * @param {string} message - User message text
   * @param {string} context - Optional additional context
   * @returns {Promise<object>} - { success, data: { success, response, error } }
   */
  aiChat: (message, context) => ipcRenderer.invoke('ai-chat', message, context),

  /**
   * Check AI Assistant availability (Ollama connectivity).
   * @returns {Promise<object>} - { success, data: { available, model, ... } }
   */
  aiStatus: () => ipcRenderer.invoke('ai-status'),

  /**
   * Clear AI Assistant conversation history.
   * @returns {Promise<object>} - { success, data: { success, message } }
   */
  aiClear: () => ipcRenderer.invoke('ai-clear'),

  /**
   * Set the Electron window title bar text.
   * @param {string} title - Title to display in the window title bar
   */
  setTitle: (title) => ipcRenderer.send('set-title', title),

  /**
   * Listen for backend error events.
   * @param {function} callback - Called with error info
   */
  onBackendError: (callback) => {
    ipcRenderer.on('backend-error', (event, data) => callback(data));
  },

  /**
   * Listen for close confirmation request from main process.
   * @param {function} callback - Called when close is requested
   */
  onConfirmClose: (callback) => {
    ipcRenderer.on('confirm-close', () => callback());
  },

  /**
   * Confirm that the user wants to close the app.
   */
  confirmClose: () => ipcRenderer.send('close-confirmed'),

  /**
   * Cancel the close action.
   */
  cancelClose: () => ipcRenderer.send('close-cancelled'),
});
