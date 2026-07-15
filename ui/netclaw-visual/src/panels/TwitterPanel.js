/**
 * TwitterPanel - Visual HUD component for NetClaw Twitter integration
 *
 * Displays recent outbound tweets and incoming mentions with real-time updates via WebSocket.
 * Shows tweet content, timestamp, category, rate limit status, and mention interactions.
 *
 * Integration:
 * 1. Import in main.js: import { TwitterPanel } from './panels/TwitterPanel.js';
 * 2. Initialize: const twitterPanel = new TwitterPanel(state.socket);
 * 3. Call twitterPanel.render() to mount the DOM element
 * 4. The panel listens for 'twitter_update' and 'twitter_mention' events on the WebSocket
 */

export class TwitterPanel {
  constructor(socket = null) {
    this.socket = socket;
    this.tweets = [];
    this.mentions = [];
    this.maxTweets = 10;
    this.maxMentions = 10;
    this.rateLimit = { remaining: 50, limit: 50, resetTime: null };
    this.element = null;
    this.isCollapsed = false;
    this.activeTab = 'tweets'; // 'tweets' or 'mentions'

    // Bind methods
    this.handleTweetUpdate = this.handleTweetUpdate.bind(this);
    this.handleRateLimitUpdate = this.handleRateLimitUpdate.bind(this);
    this.handleMentionUpdate = this.handleMentionUpdate.bind(this);
  }

  /**
   * Create and return the panel DOM element
   */
  render() {
    this.element = document.createElement('div');
    this.element.id = 'twitter-panel';
    this.element.className = 'twitter-panel';
    this.element.innerHTML = this.getTemplate();

    // Set up event listeners
    this.setupEventListeners();

    // Connect to WebSocket if available
    if (this.socket) {
      this.connectSocket();
    }

    return this.element;
  }

  /**
   * Get the panel HTML template
   */
  getTemplate() {
    return `
      <div class="twitter-panel-header">
        <div class="twitter-panel-title">
          <svg class="twitter-icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
          </svg>
          <span>Twitter</span>
        </div>
        <div class="twitter-panel-controls">
          <span class="twitter-rate-limit" title="API usage (pay-as-you-go)">
            <span class="rate-remaining">50</span>/<span class="rate-limit">50</span>
          </span>
          <button class="twitter-collapse-btn" title="Toggle panel">
            <svg viewBox="0 0 24 24" width="14" height="14">
              <path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="twitter-panel-tabs">
        <button class="twitter-tab active" data-tab="tweets">
          <span class="tab-icon">📤</span> Tweets
        </button>
        <button class="twitter-tab" data-tab="mentions">
          <span class="tab-icon">📥</span> Mentions
          <span class="mention-badge" style="display: none;">0</span>
        </button>
      </div>
      <div class="twitter-panel-content">
        <div class="twitter-tweet-list" data-content="tweets">
          <div class="twitter-empty">No tweets yet. Start posting!</div>
        </div>
        <div class="twitter-mention-list" data-content="mentions" style="display: none;">
          <div class="twitter-empty">No mentions yet. Check for @mentions!</div>
        </div>
      </div>
      <div class="twitter-panel-footer">
        <span class="twitter-status">
          <span class="status-dot"></span>
          <span class="status-text">Disconnected</span>
        </span>
      </div>
    `;
  }

  /**
   * Set up DOM event listeners
   */
  setupEventListeners() {
    // Collapse/expand button
    const collapseBtn = this.element.querySelector('.twitter-collapse-btn');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => this.toggleCollapse());
    }

    // Tab switching
    const tabs = this.element.querySelectorAll('.twitter-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });
  }

  /**
   * Switch between tweets and mentions tabs
   */
  switchTab(tabName) {
    this.activeTab = tabName;

    // Update tab buttons
    const tabs = this.element.querySelectorAll('.twitter-tab');
    tabs.forEach(tab => {
      tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update content visibility
    const tweetList = this.element.querySelector('.twitter-tweet-list');
    const mentionList = this.element.querySelector('.twitter-mention-list');

    if (tweetList) tweetList.style.display = tabName === 'tweets' ? 'block' : 'none';
    if (mentionList) mentionList.style.display = tabName === 'mentions' ? 'block' : 'none';

    // Clear mention badge when viewing mentions
    if (tabName === 'mentions') {
      const badge = this.element.querySelector('.mention-badge');
      if (badge) {
        badge.style.display = 'none';
        badge.textContent = '0';
      }
    }
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  connectSocket() {
    if (!this.socket) return;

    // Listen for tweet and mention updates
    this.socket.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'twitter_update') {
          this.handleTweetUpdate(data.payload);
        } else if (data.type === 'twitter_rate_limit') {
          this.handleRateLimitUpdate(data.payload);
        } else if (data.type === 'twitter_mention') {
          this.handleMentionUpdate(data.payload);
        } else if (data.type === 'twitter_reply_posted') {
          this.handleReplyPosted(data.payload);
        }
      } catch (e) {
        // Ignore non-JSON messages
      }
    });

    // Update connection status
    this.socket.addEventListener('open', () => this.setConnectionStatus(true));
    this.socket.addEventListener('close', () => this.setConnectionStatus(false));
    this.socket.addEventListener('error', () => this.setConnectionStatus(false));

    // Check current socket state
    if (this.socket.readyState === WebSocket.OPEN) {
      this.setConnectionStatus(true);
    }
  }

  /**
   * Handle incoming tweet update
   */
  handleTweetUpdate(tweet) {
    // Add to beginning of list
    this.tweets.unshift({
      id: tweet.tweet_id || tweet.id,
      content: tweet.content,
      category: tweet.category || 'manual',
      timestamp: tweet.timestamp || new Date().toISOString(),
      url: tweet.url || `https://twitter.com/i/web/status/${tweet.tweet_id || tweet.id}`,
      isHeartbeat: tweet.is_heartbeat || false,
    });

    // Limit to maxTweets
    if (this.tweets.length > this.maxTweets) {
      this.tweets = this.tweets.slice(0, this.maxTweets);
    }

    // Re-render tweet list
    this.renderTweets();
  }

  /**
   * Handle rate limit update
   */
  handleRateLimitUpdate(limits) {
    this.rateLimit = {
      remaining: limits.remaining || 50,
      limit: limits.limit || 50,
      resetTime: limits.reset_time || null,
    };
    this.renderRateLimit();
  }

  /**
   * Handle incoming mention update
   */
  handleMentionUpdate(mention) {
    // Add to beginning of list
    this.mentions.unshift({
      id: mention.tweet_id || mention.id,
      authorHandle: mention.author_handle,
      authorId: mention.author_id,
      text: mention.text,
      category: mention.category || 'unclassified',
      timestamp: mention.created_at || mention.timestamp || new Date().toISOString(),
      conversationId: mention.conversation_id,
      processed: mention.processed || false,
      replyId: mention.reply_id || null,
    });

    // Limit to maxMentions
    if (this.mentions.length > this.maxMentions) {
      this.mentions = this.mentions.slice(0, this.maxMentions);
    }

    // Update mention badge if not on mentions tab
    if (this.activeTab !== 'mentions') {
      const badge = this.element.querySelector('.mention-badge');
      if (badge) {
        const count = this.mentions.filter(m => !m.processed).length;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
      }
    }

    // Re-render mention list
    this.renderMentions();
  }

  /**
   * Handle reply posted event - mark mention as processed
   */
  handleReplyPosted(reply) {
    const mentionId = reply.in_reply_to_tweet_id;
    const mention = this.mentions.find(m => m.id === mentionId);
    if (mention) {
      mention.processed = true;
      mention.replyId = reply.reply_id;
      this.renderMentions();
    }
  }

  /**
   * Render the tweet list
   */
  renderTweets() {
    const listEl = this.element.querySelector('.twitter-tweet-list');
    if (!listEl) return;

    if (this.tweets.length === 0) {
      listEl.innerHTML = '<div class="twitter-empty">No tweets yet. Start posting!</div>';
      return;
    }

    listEl.innerHTML = this.tweets.map(tweet => this.getTweetHTML(tweet)).join('');
  }

  /**
   * Render the mention list
   */
  renderMentions() {
    const listEl = this.element.querySelector('.twitter-mention-list');
    if (!listEl) return;

    if (this.mentions.length === 0) {
      listEl.innerHTML = '<div class="twitter-empty">No mentions yet. Check for @mentions!</div>';
      return;
    }

    listEl.innerHTML = this.mentions.map(mention => this.getMentionHTML(mention)).join('');
  }

  /**
   * Get HTML for a single mention
   */
  getMentionHTML(mention) {
    const time = this.formatTime(mention.timestamp);
    const categoryIcon = this.getMentionCategoryIcon(mention.category);
    const statusBadge = mention.processed
      ? '<span class="mention-status replied">Replied</span>'
      : '<span class="mention-status pending">Pending</span>';

    // Truncate content for display
    const contentPreview = mention.text.length > 100
      ? mention.text.slice(0, 100) + '...'
      : mention.text;

    return `
      <div class="twitter-mention ${mention.processed ? 'processed' : ''}" data-id="${mention.id}">
        <div class="mention-header">
          <span class="mention-author">@${this.escapeHtml(mention.authorHandle)}</span>
          <span class="mention-category" title="${mention.category}">
            ${categoryIcon}
          </span>
          ${statusBadge}
          <span class="mention-time" title="${mention.timestamp}">${time}</span>
        </div>
        <div class="mention-content">${this.escapeHtml(contentPreview)}</div>
        ${mention.replyId ? `
          <a class="mention-reply-link" href="https://twitter.com/i/web/status/${mention.replyId}" target="_blank" rel="noopener">
            View reply →
          </a>
        ` : ''}
      </div>
    `;
  }

  /**
   * Get icon for mention category
   */
  getMentionCategoryIcon(category) {
    const icons = {
      netclaw_request: '🤖',
      technical_network: '🔧',
      friendly: '👋',
      off_topic: '❓',
      spam: '🚫',
      unclassified: '📝',
    };
    return icons[category] || '📝';
  }

  /**
   * Get HTML for a single tweet
   */
  getTweetHTML(tweet) {
    const time = this.formatTime(tweet.timestamp);
    const categoryIcon = this.getCategoryIcon(tweet.category);
    const heartbeatBadge = tweet.isHeartbeat ? '<span class="tweet-badge heartbeat">HB</span>' : '';

    // Truncate content for display
    const contentPreview = tweet.content.length > 120
      ? tweet.content.slice(0, 120) + '...'
      : tweet.content;

    return `
      <div class="twitter-tweet" data-id="${tweet.id}">
        <div class="tweet-header">
          <span class="tweet-category" title="${tweet.category}">
            ${categoryIcon}
          </span>
          ${heartbeatBadge}
          <span class="tweet-time" title="${tweet.timestamp}">${time}</span>
        </div>
        <div class="tweet-content">${this.escapeHtml(contentPreview)}</div>
        <a class="tweet-link" href="${tweet.url}" target="_blank" rel="noopener">
          View on X →
        </a>
      </div>
    `;
  }

  /**
   * Get icon for content category
   */
  getCategoryIcon(category) {
    const icons = {
      tip: '💡',
      hot_take: '🔥',
      til: '📚',
      achievement: '🏆',
      musing: '🤔',
      community: '👥',
      manual: '✍️',
    };
    return icons[category] || '📝';
  }

  /**
   * Format timestamp for display
   */
  formatTime(timestamp) {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);

      if (diffMins < 1) return 'now';
      if (diffMins < 60) return `${diffMins}m`;
      if (diffHours < 24) return `${diffHours}h`;

      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  }

  /**
   * Render rate limit display
   */
  renderRateLimit() {
    const remainingEl = this.element.querySelector('.rate-remaining');
    const limitEl = this.element.querySelector('.rate-limit');

    if (remainingEl) remainingEl.textContent = this.rateLimit.remaining;
    if (limitEl) limitEl.textContent = this.rateLimit.limit;

    // Color code based on remaining
    const rateLimitEl = this.element.querySelector('.twitter-rate-limit');
    if (rateLimitEl) {
      rateLimitEl.classList.remove('warning', 'critical');
      if (this.rateLimit.remaining < 10) {
        rateLimitEl.classList.add('critical');
      } else if (this.rateLimit.remaining < 20) {
        rateLimitEl.classList.add('warning');
      }
    }
  }

  /**
   * Set connection status indicator
   */
  setConnectionStatus(connected) {
    const statusDot = this.element.querySelector('.status-dot');
    const statusText = this.element.querySelector('.status-text');

    if (statusDot) {
      statusDot.classList.toggle('connected', connected);
    }
    if (statusText) {
      statusText.textContent = connected ? 'Connected' : 'Disconnected';
    }
  }

  /**
   * Toggle panel collapse state
   */
  toggleCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.element.classList.toggle('collapsed', this.isCollapsed);

    const btn = this.element.querySelector('.twitter-collapse-btn');
    if (btn) {
      btn.classList.toggle('rotated', this.isCollapsed);
    }
  }

  /**
   * Add a tweet manually (for testing or non-WebSocket updates)
   */
  addTweet(tweet) {
    this.handleTweetUpdate(tweet);
  }

  /**
   * Add a mention manually (for testing or non-WebSocket updates)
   */
  addMention(mention) {
    this.handleMentionUpdate(mention);
  }

  /**
   * Update rate limit manually
   */
  updateRateLimit(remaining, limit = 50) {
    this.handleRateLimitUpdate({ remaining, limit });
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Destroy the panel and clean up
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    this.tweets = [];
    this.mentions = [];
  }
}

// Export for ES module usage
export default TwitterPanel;
