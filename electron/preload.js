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
   * Run documentation impact assessment from validation session data.
   * @param {Array} sessionData - Array of validation JSON objects
   * @returns {Promise<object>} - { success, data: { summary, impacted_areas, ticket_impacts, timeline } }
   */
  docImpact: (sessionData) => ipcRenderer.invoke('doc-impact', sessionData),

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

  // =========================================================================
  // JIRA INTEGRATION
  // =========================================================================

  /**
   * Configure JIRA connection settings.
   * @param {object} payload - { baseUrl, userEmail, apiToken, projectKey }
   * @returns {Promise<object>} - { success, data: { configured, base_url, ... } }
   */
  jiraConfigure: (payload) => ipcRenderer.invoke('jira-configure', payload),

  /**
   * Check JIRA connection status.
   * @returns {Promise<object>} - { success, data: { configured, connected, user, ... } }
   */
  jiraStatus: () => ipcRenderer.invoke('jira-status'),

  /**
   * Fetch JIRA issues assigned to the current user.
   * @param {object} payload - { projectKey, maxResults, statusFilter }
   * @returns {Promise<object>} - { success, data: { issues, total, jql } }
   */
  jiraFetch: (payload) => ipcRenderer.invoke('jira-fetch', payload),

  /**
   * Fetch full details for a single JIRA issue.
   * @param {string} issueKey - Issue key (e.g., 'TECDOC-1234')
   * @returns {Promise<object>} - { success, data: { key, summary, description, ... } }
   */
  jiraDetail: (issueKey) => ipcRenderer.invoke('jira-detail', issueKey),

  /**
   * AI-summarize a JIRA ticket for documentation purposes.
   * @param {object} issue - Normalized issue object
   * @returns {Promise<object>} - { success, data: { summary, issue_key } }
   */
  jiraSummarize: (issue) => ipcRenderer.invoke('jira-summarize', issue),

  /**
   * Assess documentation impact of a JIRA ticket.
   * @param {object} issue - Normalized issue object
   * @returns {Promise<object>} - { success, data: { assessment, issue_key } }
   */
  jiraDocImpact: (issue) => ipcRenderer.invoke('jira-doc-impact', issue),

  /**
   * Analyze missing fields in a JIRA ticket for documentation.
   * @param {object} issue - Normalized issue object
   * @param {boolean} useAI - Whether to use AI analysis (slower but more thorough)
   * @returns {Promise<object>} - { success, data: { rule_based, ai_analysis, issue_key } }
   */
  jiraMissingFields: (issue, useAI) => ipcRenderer.invoke('jira-missing-fields', issue, useAI !== false),

  /**
   * Generate a DITA first-draft from a JIRA ticket (Neoscribe).
   * @param {object} payload - { issue, topicType, writerInstructions, existingXml }
   * @returns {Promise<object>} - { success, data: { xml, topic_type, metadata, ... } }
   */
  jiraFirstDraft: (payload) => ipcRenderer.invoke('jira-first-draft', payload),

  // =========================================================================
  // JIRA TICKET ANALYST
  // =========================================================================

  /**
   * Run full TECDOC ticket readiness analysis.
   * @param {string} issueKey - Issue key (e.g., 'TECDOC-1234')
   * @returns {Promise<object>} - { success, data: { field_validation, content_validation, readiness, ... } }
   */
  jiraAnalyzeTicket: (issueKey) => ipcRenderer.invoke('jira-analyze-ticket', issueKey),

  /**
   * Chat-based TECDOC ticket analysis (formatted for display).
   * @param {string} issueKey - Issue key (e.g., 'TECDOC-1234')
   * @param {string} question - Optional user question about the ticket
   * @returns {Promise<object>} - { success, data: { response, report } }
   */
  jiraAnalyzeChat: (issueKey, question) => ipcRenderer.invoke('jira-analyze-chat', issueKey, question),

  /**
   * Get quick summary of a JIRA ticket for dashboard display.
   * @param {string} issueKey - Issue key (e.g., 'TECDOC-1234')
   * @returns {Promise<object>} - { success, data: { key, summary, status, priority, ... } }
   */
  jiraQuickSummary: (issueKey) => ipcRenderer.invoke('jira-quick-summary', issueKey),
});
