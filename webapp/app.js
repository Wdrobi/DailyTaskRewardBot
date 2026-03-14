const tg = window.Telegram?.WebApp;
const params = new URLSearchParams(window.location.search);

const getParam = (key, fallback) => params.get(key) ?? fallback;
const getNumber = (key, fallback) => {
  const value = Number(params.get(key));
  return Number.isFinite(value) ? value : fallback;
};

const getJson = (key, fallback) => {
  const raw = params.get(key);
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
};

const state = {
  botUsername: getParam("botUsername", "dailyrichbot"),
  name: getParam("name", tg?.initDataUnsafe?.user?.first_name || "User"),
  balance: getNumber("balance", 270),
  adsToday: getNumber("adsToday", 4),
  adsLimit: getNumber("adsLimit", 30),
  referrals: getNumber("referrals", 0),
  progress: getNumber("progress", 38),
  pointsToday: getNumber("pointsToday", 24),
  tasksCompleted: getNumber("tasksCompleted", 2),
  referralReward: getNumber("referralReward", 100),
  supportUrl: getParam("supportUrl", "https://t.me/dailyrichbot"),
  tutorialUrl: getParam("tutorialUrl", "https://youtube.com/watch?v=your_video_id"),
  referralCode: getParam("ref", `start=${Math.random().toString(36).slice(2, 9)}`),
  tasks: getJson("tasks", []),
  referralUsers: getJson("referralUsers", []),
  withdrawals: getJson("withdrawals", []),
  withdrawEnabled: getParam("withdrawEnabled", "0") === "1",
};

const els = {
  avatarInitial: document.getElementById("avatarInitial"),
  miniAvatarInitial: document.getElementById("miniAvatarInitial"),
  displayName: document.getElementById("displayName"),
  balanceValue: document.getElementById("balanceValue"),
  tasksBalanceValue: document.getElementById("tasksBalanceValue"),
  walletBalanceValue: document.getElementById("walletBalanceValue"),
  adsToday: document.getElementById("adsToday"),
  referralsCount: document.getElementById("referralsCount"),
  homeTasksCompleted: document.getElementById("homeTasksCompleted"),
  goalsCounter: document.getElementById("goalsCounter"),
  goalProgressFill: document.getElementById("goalProgressFill"),
  goalHelperText: document.getElementById("goalHelperText"),
  referralTotal: document.getElementById("referralTotal"),
  referralEarnings: document.getElementById("referralEarnings"),
  referralLinkInput: document.getElementById("referralLinkInput"),
  copyReferralButton: document.getElementById("copyReferralButton"),
  shareReferralButton: document.getElementById("shareReferralButton"),
  friendCountNote: document.getElementById("friendCountNote"),
  tutorialButton: document.getElementById("tutorialButton"),
  withdrawButton: document.getElementById("withdrawButton"),
  taskListContainer: document.getElementById("taskListContainer"),
  referralListContainer: document.getElementById("referralListContainer"),
  withdrawalHistoryContainer: document.getElementById("withdrawalHistoryContainer"),
};

const currency = new Intl.NumberFormat("en-BD", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const screens = [...document.querySelectorAll(".screen")];
const navItems = [...document.querySelectorAll(".nav-item")];

function formatMoney(value) {
  return `${currency.format(value)} BDT`;
}

function referralLink() {
  return `https://t.me/${state.botUsername}?${state.referralCode}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function popup(title, message) {
  if (tg) {
    tg.HapticFeedback?.impactOccurred("light");
    tg.showPopup({
      title,
      message,
      buttons: [{ type: "ok" }],
    });
    return;
  }

  window.alert(`${title}\n\n${message}`);
}

function render() {
  const initial = state.name.trim().charAt(0).toUpperCase() || "D";
  els.avatarInitial.textContent = initial;
  els.miniAvatarInitial.textContent = initial;
  els.displayName.textContent = `Hi, ${state.name}`;
  els.balanceValue.textContent = `BDT ${currency.format(state.balance)}`;
  els.tasksBalanceValue.textContent = formatMoney(state.balance);
  els.walletBalanceValue.textContent = formatMoney(state.balance);
  els.adsToday.textContent = `${state.adsToday} / ${state.adsLimit}`;
  els.referralsCount.textContent = String(state.referrals);
  els.homeTasksCompleted.textContent = String(state.tasksCompleted);
  els.goalsCounter.textContent = `${state.adsToday} / ${state.adsLimit}`;
  els.goalProgressFill.style.width = `${Math.max(5, Math.min(state.progress, 100))}%`;
  els.goalHelperText.textContent = `You have ${Math.max(state.adsLimit - state.adsToday, 0)} tasks remaining today`;
  els.referralTotal.textContent = String(state.referrals);
  els.referralEarnings.textContent = formatMoney(state.referrals * state.referralReward);
  els.referralLinkInput.value = referralLink();
  els.friendCountNote.textContent = `${state.referrals} Friends`;
  renderTasks();
  renderReferralUsers();
  renderWithdrawals();
}

function renderTasks() {
  const tasks = state.tasks.length ? state.tasks : [
    {
      taskKey: "watch_ad",
      title: "Watch Ads",
      description: "Earn by watching ads",
      reward: 0.25,
      buttonText: "Watch Ad",
      remaining: 0,
      dailyLimit: 0,
      verifySeconds: 15,
      completed: false,
      kind: "link",
    },
  ];

  els.taskListContainer.innerHTML = tasks.map((task, index) => {
    const badge = task.completed ? "Completed" : (task.kind === "instant" ? "Instant" : (index === 0 ? "Play" : "Visit"));
    const cardClass = task.completed ? "task-card task-card-muted" : (index === 0 ? "task-card task-card-primary" : "task-card");
    const rewardClass = task.completed ? "reward-pill reward-pill-muted" : "reward-pill reward-pill-green";
    const buttonClass = task.completed ? "primary-button disabled-button" : (index % 2 === 0 ? "primary-button" : "primary-button alt-button");
    const buttonLabel = task.completed ? "Completed" : escapeHtml(task.buttonText || "Open Task");
    const footnote = task.kind === "instant"
      ? `Instant reward | Remaining: ${task.remaining} left today`
      : `Time: ${task.verifySeconds}s | Remaining: ${task.remaining} left today`;

    return `
      <article class="${cardClass}">
        <span class="task-badge${task.completed ? ' task-badge-muted' : ''}">${escapeHtml(badge)}</span>
        <div class="task-icon-bubble${task.completed ? ' muted-bubble' : ''}">${escapeHtml(task.title.slice(0, 2).toUpperCase())}</div>
        <h3>${escapeHtml(task.title)}</h3>
        <p>${escapeHtml(task.description || "Complete this task and earn reward")}</p>
        <span class="${rewardClass}">+${escapeHtml(task.reward.toFixed(2))} BDT</span>
        <button class="${buttonClass}" ${task.completed ? "disabled" : ""} data-action="${task.kind === 'instant' ? 'instant-task' : 'watch-ad'}" type="button">${buttonLabel}</button>
        <small class="card-footnote">${escapeHtml(footnote)}</small>
      </article>
    `;
  }).join("");
}

function renderReferralUsers() {
  if (!state.referralUsers.length) {
    els.referralListContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">RF</div>
        <p>You haven't invited anyone yet.</p>
        <small>Share your link to start earning!</small>
      </div>
    `;
    return;
  }

  els.referralListContainer.innerHTML = `
    <div class="data-list">
      ${state.referralUsers.map((item) => `
        <div class="data-list-item">
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <small>Joined ${escapeHtml(item.joinedAt)}</small>
          </div>
          <strong>+${escapeHtml(Number(item.earned).toFixed(2))} BDT</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function renderWithdrawals() {
  els.withdrawButton.disabled = !state.withdrawEnabled;
  if (!state.withdrawEnabled) {
    els.withdrawButton.textContent = "Withdrawal Coming Soon";
  }

  if (!state.withdrawals.length) {
    els.withdrawalHistoryContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">WH</div>
        <p>No withdrawal history found.</p>
      </div>
    `;
    return;
  }

  els.withdrawalHistoryContainer.innerHTML = `
    <div class="data-list">
      ${state.withdrawals.map((item) => `
        <div class="data-list-item">
          <div>
            <strong>${escapeHtml(item.method)}</strong>
            <small>${escapeHtml(item.date)}</small>
          </div>
          <div>
            <strong>${escapeHtml(Number(item.amount).toFixed(2))} BDT</strong>
            <div class="status-chip ${escapeHtml(item.status)}">${escapeHtml(item.status)}</div>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

function activateScreen(screenName) {
  screens.forEach((screen) => {
    screen.classList.toggle("is-active", screen.dataset.screen === screenName);
  });

  navItems.forEach((item) => {
    item.classList.toggle("active", item.dataset.target === screenName);
  });

  if (tg) {
    tg.MainButton.offClick(handleMainButton);
    tg.MainButton.hide();
  }
}

function handleMainButton() {
  tg?.MainButton.hide();
}

function handleAction(action, explicitTarget) {
  const target = explicitTarget || action;

  if (["home", "support", "tasks", "referral", "wallet"].includes(target)) {
    activateScreen(target);
    return;
  }

  if (action === "leaderboard") {
    popup("Leaderboard", "Leaderboard backend sync next step-এ connect করা হবে।");
    return;
  }

  if (action === "watch-ad") {
    popup("Watch Ad", "এখানে bot task বা real ad endpoint connect হবে।");
    return;
  }

  if (action === "instant-task") {
    popup("Instant Task", "এই instant task bot backend-এর সাথে sync হবে।");
    return;
  }

  if (action === "visit-site") {
    popup("Visit Site", "এখানে DB-driven site visit task connect হবে।");
    return;
  }

  if (action === "withdraw") {
    popup("Withdrawal", "Payment integration ready হলে এখান থেকে request যাবে।");
    return;
  }

  if (action === "telegram-support") {
    window.open(state.supportUrl, "_blank", "noopener,noreferrer");
    return;
  }

  if (action === "email-support") {
    window.location.href = "mailto:support@example.com?subject=Daily%20Rich%20Support";
    return;
  }

  if (action === "faq") {
    popup("FAQ", "FAQ content next step-এ dynamic content হিসেবে load হবে।");
    return;
  }

  if (action === "live-chat") {
    popup("Live Chat", "Live chat provider connect করলে এই section কাজ করবে।");
    return;
  }

  if (action === "tutorial") {
    window.open(state.tutorialUrl, "_blank", "noopener,noreferrer");
    return;
  }

  if (action === "copy-referral") {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(referralLink()).then(() => {
        popup("Copied", "Referral link copied successfully.");
      }).catch(() => {
        popup("Copy Failed", "Referral link copy করা যায়নি।");
      });
      return;
    }

    els.referralLinkInput.focus();
    els.referralLinkInput.select();
    document.execCommand("copy");
    popup("Copied", "Referral link copied successfully.");
    return;
  }

  if (action === "share-referral") {
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(referralLink())}&text=${encodeURIComponent("Join Daily Rich and start earning")}`;
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(shareUrl);
    } else {
      window.open(shareUrl, "_blank", "noopener,noreferrer");
    }
  }
}

function bindEvents() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => handleAction(button.dataset.action, button.dataset.target));
  });

  navItems.forEach((button) => {
    button.addEventListener("click", () => activateScreen(button.dataset.target));
  });

  els.copyReferralButton.addEventListener("click", () => handleAction("copy-referral"));
  els.shareReferralButton.addEventListener("click", () => handleAction("share-referral"));
  els.tutorialButton.addEventListener("click", () => handleAction("tutorial"));
  els.withdrawButton.addEventListener("click", () => handleAction("withdraw"));
}

function initTelegram() {
  if (!tg) {
    return;
  }

  tg.ready();
  tg.expand();
  tg.setHeaderColor("#3a1428");
  tg.setBackgroundColor("#181624");
  tg.MainButton.hide();
}

render();
bindEvents();
initTelegram();
activateScreen("home");
