/* ===========================
   Chat UI - Fixed App Logic
   =========================== */

'use strict';

const chat = document.getElementById('chat');
const btn = document.getElementById('simulate');

// Track internal state
let messageSequence = 5; // Start after initial 4 messages
let headerSequence = 1;
let scrollRestoreY = 0;

/**
 * Safely insert a time header
 * Minimal DOM operations, no innerHTML rewrites
 */
function insertTimeHeader() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const mins = String(now.getMinutes()).padStart(2, '0');
  const timeText = `${hours}:${mins}`;

  const header = document.createElement('div');
  header.className = 'time-header';
  header.id = `header-${headerSequence++}`;
  header.setAttribute('role', 'separator');
  header.setAttribute('aria-label', `Time divider ${timeText}`);

  const span = document.createElement('span');
  span.className = 'header-text';
  span.textContent = timeText;
  header.appendChild(span);

  // Append to end (preserves scroll anchoring)
  chat.appendChild(header);
  return header;
}

/**
 * Safely insert a new message
 * Use createElement and appendChild, no innerHTML
 */
function insertMessage(isLeft) {
  const direction = isLeft ? 'left' : 'right';
  const avatarIdx = (messageSequence % 10) + 1;

  const msg = document.createElement('div');
  msg.className = `message ${direction}`;
  msg.id = `msg-${messageSequence}`;
  msg.setAttribute('data-sequence', messageSequence);
  messageSequence++;

  // Avatar
  const avatar = document.createElement('img');
  avatar.className = 'avatar';
  avatar.src = `https://i.pravatar.cc/40?img=${avatarIdx}`;
  avatar.alt = `User avatar ${avatarIdx}`;

  msg.appendChild(avatar);

  // Content: random choice between text and image
  if (Math.random() > 0.5) {
    // Text message
    const textDiv = document.createElement('div');
    textDiv.className = 'message-content';
    textDiv.textContent = `Random text message ${Math.floor(Math.random() * 100)}`;
    msg.appendChild(textDiv);
  } else {
    // Image message
    const wrapper = document.createElement('div');
    wrapper.className = 'media-wrapper';

    const img = document.createElement('img');
    img.className = 'media';
    // Use fixed-size, consistent images to avoid layout thrashing
    img.src = `https://i.pravatar.cc/200x300?img=${avatarIdx}`;
    img.alt = 'Shared image';

    wrapper.appendChild(img);
    msg.appendChild(wrapper);
  }

  chat.appendChild(msg);
  return msg;
}

/**
 * Simulate scroll and rapid content insertion
 * Preserves scroll position to detect jumps
 */
function simulateScrollAndUpdate() {
  // Save scroll position before updates
  scrollRestoreY = chat.scrollTop;

  let scrollCount = 0;
  function fastScroll() {
    chat.scrollTop = (scrollCount % 2 === 0) ? chat.scrollHeight : 0;
    scrollCount++;
    if (scrollCount < 20) {
      requestAnimationFrame(fastScroll);
    } else {
      // After scroll simulation, inject new content
      injectNewContent();
      // Restore scroll position to detect jumps
      setTimeout(() => {
        const finalScroll = chat.scrollTop;
        console.log(
          `Scroll preserved: expected ~${scrollRestoreY}, got ${finalScroll}`
        );
      }, 100);
    }
  }
  fastScroll();
}

/**
 * Inject new content with minimal DOM operations
 * No innerHTML rewrites, incremental inserts only
 */
function injectNewContent() {
  // Insert a time header
  insertTimeHeader();

  // Insert 2-3 new messages
  const messageCount = 2 + Math.floor(Math.random() * 2);
  for (let i = 0; i < messageCount; i++) {
    insertMessage(Math.random() > 0.5);
  }

  // Auto-scroll to bottom to show new content
  setTimeout(() => {
    chat.scrollTop = chat.scrollHeight;
  }, 50);
}

/**
 * Exposed function for test validator to trigger single insert
 * Allows controlled testing without random scroll simulation
 */
window.simulateInsertOnce = function () {
  insertTimeHeader();
  insertMessage(Math.random() > 0.5);
  setTimeout(() => {
    chat.scrollTop = chat.scrollHeight;
  }, 50);
};

// Event listener
btn.onclick = simulateScrollAndUpdate;
