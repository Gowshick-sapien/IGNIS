/* IGNIS Interactive Report Script */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initTocHighlight();
  initSearch();
  initExpandCollapse();
  initKeyboardShortcuts();
});

// Theme Management
function initThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle');
  const savedTheme = localStorage.getItem('ignis_theme') || 'dark';
  document.body.setAttribute('data-theme', savedTheme);
  updateThemeBtnText(toggleBtn, savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const currentTheme = document.body.getAttribute('data-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.body.setAttribute('data-theme', newTheme);
      localStorage.setItem('ignis_theme', newTheme);
      updateThemeBtnText(toggleBtn, newTheme);
    });
  }
}

function updateThemeBtnText(btn, theme) {
  if (btn) {
    btn.textContent = theme === 'light' ? 'Dark Mode' : 'Light Mode';
  }
}

// Sidebar TOC Highlight via IntersectionObserver
function initTocHighlight() {
  const observerOptions = {
    root: null,
    rootMargin: '-20% 0px -70% 0px',
    threshold: 0
  };

  const sections = document.querySelectorAll('section[id], details[id], div[id]');
  const navLinks = document.querySelectorAll('.toc-item a');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute('id');
        navLinks.forEach(link => {
          if (link.getAttribute('href') === `#${id}`) {
            link.classList.add('active');
          } else {
            link.classList.remove('active');
          }
        });
      }
    });
  }, observerOptions);

  sections.forEach(section => observer.observe(section));
}

// Live Full-Text Search
let searchMatches = [];
let currentMatchIndex = -1;

function initSearch() {
  const searchInput = document.getElementById('report-search');
  const matchCounter = document.getElementById('search-match-count');

  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim().toLowerCase();
    clearHighlights();
    searchMatches = [];
    currentMatchIndex = -1;

    if (!query) {
      if (matchCounter) matchCounter.textContent = '0 matches';
      return;
    }

    const contentArea = document.querySelector('.main-content');
    highlightText(contentArea, query);

    searchMatches = Array.from(document.querySelectorAll('mark.search-mark'));
    if (matchCounter) {
      matchCounter.textContent = `${searchMatches.length} matches`;
    }

    if (searchMatches.length > 0) {
      currentMatchIndex = 0;
      focusMatch(currentMatchIndex);
    }
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (searchMatches.length === 0) return;
      if (e.shiftKey) {
        currentMatchIndex = (currentMatchIndex - 1 + searchMatches.length) % searchMatches.length;
      } else {
        currentMatchIndex = (currentMatchIndex + 1) % searchMatches.length;
      }
      focusMatch(currentMatchIndex);
    }
  });
}

function highlightText(element, query) {
  if (element.nodeType === Node.TEXT_NODE) {
    const text = element.textContent;
    const lowerText = text.toLowerCase();
    const index = lowerText.indexOf(query);

    if (index >= 0 && element.parentNode && !['SCRIPT', 'STYLE', 'MARK'].includes(element.parentNode.nodeName)) {
      const matchText = text.substring(index, index + query.length);
      const afterText = text.substring(index + query.length);
      element.textContent = text.substring(0, index);

      const mark = document.createElement('mark');
      mark.className = 'search-mark';
      mark.textContent = matchText;

      const afterNode = document.createTextNode(afterText);
      element.parentNode.insertBefore(mark, element.nextSibling);
      element.parentNode.insertBefore(afterNode, mark.nextSibling);

      // Open parent details if collapsed
      let parentDetails = mark.closest('details');
      if (parentDetails) {
        parentDetails.open = true;
      }
    }
  } else {
    element.childNodes.forEach(child => highlightText(child, query));
  }
}

function clearHighlights() {
  document.querySelectorAll('mark.search-mark').forEach(mark => {
    const parent = mark.parentNode;
    parent.replaceChild(document.createTextNode(mark.textContent), mark);
    parent.normalize();
  });
}

function focusMatch(index) {
  searchMatches.forEach((m, idx) => {
    m.style.outline = idx === index ? '2px solid var(--accent-blue)' : 'none';
  });
  if (searchMatches[index]) {
    searchMatches[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// Expand / Collapse All
function initExpandCollapse() {
  const expandBtn = document.getElementById('expand-all');
  const collapseBtn = document.getElementById('collapse-all');
  const details = document.querySelectorAll('details.scenario-section');

  if (expandBtn) {
    expandBtn.addEventListener('click', () => {
      details.forEach(d => d.open = true);
    });
  }

  if (collapseBtn) {
    collapseBtn.addEventListener('click', () => {
      details.forEach(d => d.open = false);
    });
  }
}

// Keyboard Shortcuts
function initKeyboardShortcuts() {
  const searchInput = document.getElementById('report-search');
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey && e.key === 'f') || e.key === '/') {
      if (document.activeElement !== searchInput) {
        e.preventDefault();
        if (searchInput) searchInput.focus();
      }
    } else if (e.key === 'Escape') {
      if (document.activeElement === searchInput) {
        searchInput.blur();
      }
      clearHighlights();
      searchMatches = [];
      const matchCounter = document.getElementById('search-match-count');
      if (matchCounter) matchCounter.textContent = '0 matches';
    }
  });
}
