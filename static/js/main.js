(function () {
  const input = document.getElementById('profile-id-input');
  const btn = document.getElementById('search-btn');
  const loadProfileBtn = document.getElementById('load-profile-btn');
  const cancelBtn = document.getElementById('cancel-btn');
  const statusArea = document.getElementById('status-area');
  const resultsArea = document.getElementById('results-area');

  let pollTimer = null;
  let currentJobId = null;

  btn.addEventListener('click', startSearch);
  loadProfileBtn.addEventListener('click', loadProfile);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') startSearch();
  });
  cancelBtn.addEventListener('click', function () {
    if (currentJobId) {
      fetch('/api/job/' + currentJobId + '/cancel', { method: 'POST' }).catch(() => {});
      currentJobId = null;
    }
    clearPoll();
    setStatus('');
    resultsArea.innerHTML = '';
    btn.disabled = false;
    loadProfileBtn.disabled = false;
    cancelBtn.style.display = 'none';
  });

  function loadProfile() {
    const profileId = input.value.trim();
    if (!profileId) return;

    clearPoll();
    resultsArea.innerHTML = '';
    setStatus('<span class="spinner"></span> Loading profile…');
    btn.disabled = true;
    loadProfileBtn.disabled = true;

    fetch('/load-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          showError(data.error);
          btn.disabled = false;
          loadProfileBtn.disabled = false;
          return;
        }
        pollLoadProfile(data.job_id, data.source_site);
      })
      .catch(err => {
        showError('Request failed: ' + err.message);
        btn.disabled = false;
        loadProfileBtn.disabled = false;
      });
  }

  function pollLoadProfile(jobId, sourceSite) {
    currentJobId = jobId;
    cancelBtn.style.display = '';

    pollTimer = setInterval(function () {
      fetch('/api/job/' + jobId)
        .then(r => r.json())
        .then(job => {
          if (job.status === 'done') {
            clearPoll();
            currentJobId = null;
            setStatus('');
            btn.disabled = false;
            loadProfileBtn.disabled = false;
            cancelBtn.style.display = 'none';
            if (job.result && job.result.source) {
              showSourcePanel(job.result.source, sourceSite);
            }
          } else if (job.status === 'error') {
            clearPoll();
            currentJobId = null;
            showError(job.error || 'An error occurred.');
            setStatus('');
            btn.disabled = false;
            loadProfileBtn.disabled = false;
            cancelBtn.style.display = 'none';
          }
        })
        .catch(() => {});
    }, 2000);
  }

  function startSearch() {
    const profileId = input.value.trim();
    if (!profileId) return;

    clearPoll();
    resultsArea.innerHTML = '';
    setStatus('<span class="spinner"></span> Starting…');
    btn.disabled = true;
    loadProfileBtn.disabled = true;

    fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          showError(data.error);
          btn.disabled = false;
          loadProfileBtn.disabled = false;
          return;
        }
        if (data.cached) {
          showCachedMatch(data.match, data.source_site, profileId);
          setStatus('');
          btn.disabled = false;
          loadProfileBtn.disabled = false;
          return;
        }
        pollJob(data.job_id, profileId, data.source_site);
      })
      .catch(err => {
        showError('Request failed: ' + err.message);
        btn.disabled = false;
        loadProfileBtn.disabled = false;
      });
  }

  function pollJob(jobId, sourceId, sourceSite) {
    currentJobId = jobId;
    setStatus('<span class="spinner"></span> Searching and comparing faces...');
    cancelBtn.style.display = '';
    let sourceRendered = false;

    pollTimer = setInterval(function () {
      fetch('/api/job/' + jobId)
        .then(r => r.json())
        .then(job => {
          // Show source profile as soon as it's available
          if (!sourceRendered && job.result && job.result.source) {
            showSourcePanel(job.result.source, sourceSite);
            sourceRendered = true;
          }

          if (job.status === 'done') {
            clearPoll();
            currentJobId = null;
            setStatus('');
            btn.disabled = false;
            loadProfileBtn.disabled = false;
            cancelBtn.style.display = 'none';
            showMatches(job.result, sourceSite);
          } else if (job.status === 'error') {
            clearPoll();
            currentJobId = null;
            showError(job.error || 'An error occurred.');
            setStatus('');
            btn.disabled = false;
            loadProfileBtn.disabled = false;
            cancelBtn.style.display = 'none';
          }
        })
        .catch(() => {});
    }, 2000);
  }

  function clearPoll() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function setStatus(html) { statusArea.innerHTML = html; }

  function showError(msg) {
    resultsArea.innerHTML = '<div class="error-msg">' + escHtml(msg) + '</div>';
  }

  function showCachedMatch(match, sourceSite, sourceId) {
    const targetSite = sourceSite === 'an' ? 'AS' : 'AN';
    const targetId = sourceSite === 'an' ? match.as_id : match.an_id;
    resultsArea.innerHTML =
      '<div class="cached-match">' +
      '<strong>Previously confirmed match found</strong><br>' +
      targetSite + ' ID: <strong>' + escHtml(targetId) + '</strong>' +
      '</div>';
  }

  function showSourcePanel(src, sourceSite) {
    // Idempotent — if panel already exists, update it in place
    let srcPanel = resultsArea.querySelector('.source-panel');
    if (!srcPanel) {
      srcPanel = document.createElement('div');
      srcPanel.className = 'source-panel';
      resultsArea.insertBefore(srcPanel, resultsArea.firstChild);
    }
    const srcImgs = src.image_urls && src.image_urls.length ? src.image_urls : (src.first_image_url ? [src.first_image_url] : []);
    const srcSiteLabel = sourceSite === 'an' ? 'AN' : 'AS';
    const imgsHtml = srcImgs.length
      ? srcImgs.map(function (u) { return '<img src="' + escHtml(u) + '" alt="source profile">'; }).join('')
      : '<div class="no-image">No image</div>';
    srcPanel.innerHTML =
      '<div class="source-img">' + imgsHtml + '</div>' +
      '<div class="source-info">' +
        '<div class="source-label">Searching for</div>' +
        '<div class="source-id">' + escHtml(srcSiteLabel) + ': <strong>' + escHtml(src.profile_id) + '</strong></div>' +
        (src.name ? '<div>' + escHtml(src.name) + '</div>' : '') +
        (src.dob ? '<div>DOB: ' + escHtml(src.dob) + '</div>' : '') +
        (src.age ? '<div>' + src.age + ' yrs' + (src.height_cm ? ' &nbsp;|&nbsp; ' + src.height_cm + ' cm' : '') + '</div>' : '') +
        (src.nakshatra ? '<div>' + escHtml(src.nakshatra) + (src.rashi ? ' &nbsp;|&nbsp; ' + escHtml(src.rashi) : '') + '</div>' : '') +
        (src.gotra ? '<div>Gotra: ' + escHtml(src.gotra) + '</div>' : '') +
      '</div>';
  }

  function showMatches(result, sourceSite) {
    // Remove any existing matches section before re-rendering
    const existing = resultsArea.querySelector('.matches-section');
    if (existing) existing.remove();

    if (!result || !result.matches || result.matches.length === 0) {
      const msg = document.createElement('div');
      msg.className = 'error-msg';
      msg.textContent = 'No candidates found. Try a different profile or check the search filters.';
      resultsArea.appendChild(msg);
      return;
    }

    const section = document.createElement('div');
    section.className = 'matches-section';

    const heading = document.createElement('h3');
    heading.className = 'matches-heading';
    heading.textContent = 'Matches on ' + (sourceSite === 'an' ? 'AS' : 'AN');
    section.appendChild(heading);

    const targetSite = sourceSite === 'an' ? 'AS' : 'AN';
    const grid = document.createElement('div');
    grid.className = 'results-grid';

    result.matches.forEach(function (match, idx) {
      const profile = match.profile;
      const card = document.createElement('div');
      card.className = 'result-card' + (idx === 0 ? ' top-match' : '');

      const imgUrls = profile.image_urls || [];
      const firstImg = imgUrls[0] || profile.first_image_url;

      let imgHtml;
      if (firstImg) {
        imgHtml = '<img src="' + escHtml(firstImg) + '" alt="profile photo" loading="lazy">';
      } else {
        imgHtml = '<div class="no-image">No image</div>';
      }

      const confClass = match.confidence >= 70 ? 'high' : match.confidence >= 50 ? 'medium' : 'low';

      const anId = sourceSite === 'an' ? result.source.profile_id : profile.profile_id;
      const asId = sourceSite === 'as' ? result.source.profile_id : profile.profile_id;

      card.innerHTML =
        (idx === 0 ? '<span class="badge-top">Best match</span>' : '') +
        imgHtml +
        '<div class="result-info">' +
          '<div class="profile-id">' + escHtml(targetSite) + ': ' + escHtml(profile.profile_id) + '</div>' +
          (profile.name ? '<div class="profile-name">' + escHtml(profile.name) + '</div>' : '') +
          (profile.dob ? '<div class="profile-dob">DOB: ' + escHtml(profile.dob) + '</div>' : '') +
          '<div class="confidence ' + confClass + '">' + match.confidence.toFixed(1) + '% match</div>' +
          '<div class="result-actions">' +
            '<button class="btn-yes" data-an="' + escHtml(anId) + '" data-as="' + escHtml(asId) + '">Yes</button>' +
            '<button class="btn-no">No</button>' +
          '</div>' +
        '</div>';

      card.querySelector('.btn-yes').addEventListener('click', function () {
        confirmMatch(this.dataset.an, this.dataset.as, card);
      });
      card.querySelector('.btn-no').addEventListener('click', function () {
        card.style.opacity = '0.35';
      });

      grid.appendChild(card);
    });

    section.appendChild(grid);
    resultsArea.appendChild(section);
  }

  function confirmMatch(anId, asId, card) {
    fetch('/api/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ an_id: anId, as_id: asId }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          card.classList.add('confirmed');
          card.querySelector('.result-actions').innerHTML = '<strong style="color:#28a745">Confirmed</strong>';
        }
      })
      .catch(() => {});
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();
