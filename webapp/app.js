const tg = window.Telegram?.WebApp;
const params = new URLSearchParams(window.location.search);
const DAILY_AD_LIMIT = 30;

const getParam = (key, fallback) => params.get(key) ?? fallback;
const getNumber = (key, fallback) => {
  const raw = params.get(key);
  if (raw === null) return fallback;
  const value = Number(raw);
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
  adsLimit: DAILY_AD_LIMIT,
  referrals: getNumber("referrals", 0),
  progress: getNumber("progress", 38),
  pointsToday: getNumber("pointsToday", 24),
  tasksCompleted: getNumber("tasksCompleted", 2),
  referralReward: getNumber("referralReward", 50),
  supportUrl: getParam("supportUrl", "https://t.me/dailyrichbot"),
  tutorialUrl: getParam("tutorialUrl", "https://youtube.com/watch?v=your_video_id"),
  referralCode: getParam("ref", `start=${Math.random().toString(36).slice(2, 9)}`),
  tasks: getJson("tasks", []),
  referralUsers: getJson("referralUsers", []),
  withdrawals: getJson("withdrawals", []),
  withdrawEnabled: getParam("withdrawEnabled", "0") === "1",
  minWithdrawBdt: getNumber("minWithdrawBdt", 500),
  minActiveReferrals: getNumber("minActiveReferrals", 10),
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
  referralRewardHeader: document.getElementById("referralRewardHeader"),
  referralRewardBanner: document.getElementById("referralRewardBanner"),
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

function taskIconMarkup(taskKey) {
  const icons = {
    watch_ad: `
      <svg class="task-glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="4" y="6" width="16" height="12" rx="3" stroke="currentColor" stroke-width="1.8"/>
        <path d="M10 9.5v5l4-2.5-4-2.5Z" fill="currentColor"/>
      </svg>
    `,
    visit_site: `
      <svg class="task-glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.8"/>
        <path d="M4.5 12h15M12 4.5c2.2 2.25 3.4 4.75 3.4 7.5S14.2 17.25 12 19.5M12 4.5c-2.2 2.25-3.4 4.75-3.4 7.5s1.2 5.25 3.4 7.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
      </svg>
    `,
    daily_checkin: `
      <svg class="task-glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="10" cy="12" r="4.5" stroke="currentColor" stroke-width="1.8"/>
        <circle cx="14.5" cy="10" r="4" stroke="currentColor" stroke-width="1.8" opacity="0.75"/>
        <path d="M10 9.5v5M8 11.3h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    `,
  };

  return icons[taskKey] || `
    <svg class="task-glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M8 7h11M8 12h11M8 17h11M4.5 7.25h.5M4.5 12.25h.5M4.5 17.25h.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `;
}

function render() {
  const initial = state.name.trim().charAt(0).toUpperCase() || "D";
  els.avatarInitial.textContent = initial;
  els.miniAvatarInitial.textContent = initial;
  els.displayName.textContent = `Hi, ${state.name} 👋`;
  els.balanceValue.textContent = `BDT ${currency.format(state.balance)}`;
  els.tasksBalanceValue.textContent = formatMoney(state.balance);
  els.walletBalanceValue.textContent = formatMoney(state.balance);
  els.adsToday.textContent = `${state.adsToday} / ${state.adsLimit}`;
  els.referralsCount.textContent = String(state.referrals);
  els.homeTasksCompleted.textContent = String(state.tasksCompleted);
  els.goalsCounter.textContent = `${state.adsToday} / ${state.adsLimit}`;
  const progressPercent = state.adsLimit > 0
    ? Math.min((state.adsToday / state.adsLimit) * 100, 100)
    : 0;
  els.goalProgressFill.style.width = `${Math.max(progressPercent, 0)}%`;
  els.goalHelperText.textContent = `You have ${Math.max(state.adsLimit - state.adsToday, 0)} tasks remaining today`;
  els.referralTotal.textContent = String(state.referrals);
  els.referralEarnings.textContent = formatMoney(state.referrals * state.referralReward);
  if (els.referralRewardHeader) els.referralRewardHeader.textContent = formatMoney(state.referralReward);
  if (els.referralRewardBanner) els.referralRewardBanner.textContent = formatMoney(state.referralReward);
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
      reward: 4.00,
      buttonText: "Watch Ad",
      remaining: Math.max(DAILY_AD_LIMIT - state.adsToday, 0),
      dailyLimit: DAILY_AD_LIMIT,
      verifySeconds: 15,
      completed: false,
      kind: "link",
    },
    {
      taskKey: "visit_site",
      title: "Website Visit",
      description: "Visit the sponsor website and stay for a few seconds",
      reward: 5.00,
      buttonText: "Visit Website",
      remaining: 15,
      dailyLimit: 15,
      verifySeconds: 10,
      completed: false,
      kind: "link",
    },
    {
      taskKey: "daily_checkin",
      title: "Daily Check-In",
      description: "Claim your instant daily bonus once per day",
      reward: 3.00,
      buttonText: "Claim Bonus",
      remaining: 1,
      dailyLimit: 1,
      verifySeconds: 0,
      completed: false,
      kind: "instant",
    },
  ];

  els.taskListContainer.innerHTML = tasks.map((task, index) => {
    const isWatchAdTask = task.taskKey === "watch_ad";
    const taskCompleted = isWatchAdTask ? state.adsToday >= DAILY_AD_LIMIT : Boolean(task.completed);
    const remainingToday = isWatchAdTask
      ? Math.max(DAILY_AD_LIMIT - state.adsToday, 0)
      : Math.max(Number(task.remaining ?? 0), 0);
    const badge = taskCompleted ? "Completed" : (task.kind === "instant" ? "Instant" : (index === 0 ? "Play" : "Visit"));
    const cardClass = taskCompleted ? "task-card task-card-muted" : (index === 0 ? "task-card task-card-primary" : "task-card");
    const rewardClass = taskCompleted ? "reward-pill reward-pill-muted" : "reward-pill reward-pill-green";
    const buttonClass = taskCompleted ? "primary-button disabled-button" : (index % 2 === 0 ? "primary-button" : "primary-button alt-button");
    const buttonLabel = taskCompleted ? "Completed" : escapeHtml(task.buttonText || "Open Task");
    const actionName = task.kind === "instant"
      ? "instant-task"
      : (task.taskKey === "visit_site" ? "visit-site" : "watch-ad");
    const footnote = task.kind === "instant"
      ? `Instant reward | Remaining: ${remainingToday} left today`
      : `Time: ${task.verifySeconds}s | Remaining: ${remainingToday} left today`;

    return `
      <article class="${cardClass}">
        <span class="task-badge${taskCompleted ? ' task-badge-muted' : ''}">${escapeHtml(badge)}</span>
        <div class="task-icon-bubble task-icon-${escapeHtml(task.taskKey || 'default').replaceAll('_', '-')}${taskCompleted ? ' muted-bubble' : ''}">${taskIconMarkup(task.taskKey)}</div>
        <h3>${escapeHtml(task.title)}</h3>
        <p>${escapeHtml(task.description || "Complete this task and earn reward")}</p>
        <span class="${rewardClass}">+${escapeHtml(task.reward.toFixed(2))} BDT</span>
        <button class="${buttonClass}" ${taskCompleted ? "disabled" : ""} data-action="${actionName}" type="button">${buttonLabel}</button>
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
  els.withdrawButton.disabled = false;
  if (!state.withdrawEnabled) {
    els.withdrawButton.textContent = "Withdrawal Disabled";
  } else {
    els.withdrawButton.textContent = "Use Bot Wallet";
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
    if (state.adsToday >= state.adsLimit) {
      popup("Limit Reached", "আজকের জন্য সর্বোচ্চ " + state.adsLimit + "টি বিজ্ঞাপন দেখা হয়ে গেছে।");
      return;
    }
    if (typeof show_10728950 !== "function") {
      popup("Please Wait", "Ad network লোড হচ্ছে। একটু পর আবার চেষ্টা করুন।");
      return;
    }
    // Rewarded Interstitial
    show_10728950().then(() => {
      state.adsToday += 1;
      state.balance += 4;
      render();
      popup("Reward Earned! 🎉", "আপনি 4.00 BDT পুরস্কার পেয়েছেন বিজ্ঞাপন দেখার জন্য!");
    });
    return;
  }

  if (action === "instant-task") {
    popup("Instant Task", "এই instant task bot backend-এর সাথে sync হবে।");
    return;
  }

  if (action === "visit-site") {
    if (typeof show_10728950 !== "function") {
      popup("Please Wait", "Ad network লোড হচ্ছে। একটু পর আবার চেষ্টা করুন।");
      return;
    }
    // Rewarded Popup
    show_10728950("pop").then(() => {
      state.balance += 5;
      render();
      popup("Reward Earned! 🎉", "আপনি 5.00 BDT পুরস্কার পেয়েছেন সাইট ভিজিট করার জন্য!");
    }).catch(() => {
      // user closed or error — no reward, do nothing
    });
    return;
  }

  if (action === "withdraw") {
    const walletUrl = `https://t.me/${state.botUsername}?start=wallet`;
    if (state.withdrawEnabled) {
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(walletUrl);
      } else {
        window.open(walletUrl, "_blank", "noopener,noreferrer");
      }
      return;
    }
    popup(
      "Withdrawal",
      `Withdrawal এখন disabled আছে. Enable হলে bot wallet থেকে request করা যাবে. Requirement: ${state.minWithdrawBdt.toFixed(0)} BDT and ${state.minActiveReferrals.toFixed(0)} active referrals.`
    );
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
  if (els.tutorialButton) {
    els.tutorialButton.addEventListener("click", () => handleAction("tutorial"));
  }
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

  // In-App Interstitial — passive background ads, no reward required
  if (typeof show_10728950 === "function") {
    show_10728950({
      type: "inApp",
      inAppSettings: {
        frequency: 2,
        capping: 0.1,
        interval: 30,
        timeout: 5,
        everyPage: false,
      },
    });
  }
}

render();
bindEvents();
initTelegram();
activateScreen("home");
