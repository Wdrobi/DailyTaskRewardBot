const tg = window.Telegram?.WebApp;
const params = new URLSearchParams(window.location.search);
const runtimeOrigin = window.location.origin;
const defaultApiBase = (runtimeOrigin && runtimeOrigin !== "null" && !runtimeOrigin.startsWith("file"))
  ? runtimeOrigin
  : "http://localhost:8080";

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

function buildFallbackTasks(adsLimit) {
  return [
    {
      taskKey: "watch_ad",
      title: "Watch Ads",
      description: "Earn by watching ads",
      reward: 4.0,
      buttonText: "Watch Ad",
      remaining: adsLimit,
      completedCount: 0,
      dailyLimit: adsLimit,
      verifySeconds: 15,
      completed: false,
      kind: "link",
      url: "",
    },
    {
      taskKey: "visit_site",
      title: "Website Visit",
      description: "Visit the sponsor website and stay for a few seconds",
      reward: 5.0,
      buttonText: "Visit Website",
      remaining: 15,
      completedCount: 0,
      dailyLimit: 15,
      verifySeconds: 10,
      completed: false,
      kind: "link",
      url: "",
    },
    {
      taskKey: "daily_checkin",
      title: "Daily Check-In",
      description: "Claim your instant daily bonus once per day",
      reward: 3.0,
      buttonText: "Claim Bonus",
      remaining: 1,
      completedCount: 0,
      dailyLimit: 1,
      verifySeconds: 0,
      completed: false,
      kind: "instant",
      url: "",
    },
  ];
}

function normalizeTask(task) {
  const dailyLimit = Math.max(Number(task.dailyLimit ?? 1) || 1, 1);
  const remaining = Math.max(Number(task.remaining ?? dailyLimit) || 0, 0);
  const inferredCompleted = Math.max(dailyLimit - remaining, 0);
  const rawCompleted = Number(task.completedCount ?? inferredCompleted);
  const completedCount = Math.min(Math.max(rawCompleted || 0, inferredCompleted), dailyLimit);

  return {
    taskKey: String(task.taskKey || "task"),
    title: String(task.title || "Task"),
    description: String(task.description || "Complete this task and earn reward"),
    reward: Number(task.reward || 0),
    buttonText: String(task.buttonText || "Open Task"),
    remaining: Math.max(dailyLimit - completedCount, 0),
    completedCount,
    dailyLimit,
    verifySeconds: Math.max(Number(task.verifySeconds || 0), 0),
    completed: Boolean(task.completed) || completedCount >= dailyLimit,
    kind: String(task.kind || "link"),
    url: String(task.url || ""),
  };
}

function getTaskStats() {
  const totalLimit = state.tasks.reduce((sum, task) => sum + task.dailyLimit, 0);
  const totalCompleted = state.tasks.reduce((sum, task) => sum + task.completedCount, 0);
  const watchAdTask = state.tasks.find((task) => task.taskKey === "watch_ad");

  return {
    totalLimit,
    totalCompleted,
    remainingTotal: Math.max(totalLimit - totalCompleted, 0),
    watchAdCompleted: watchAdTask ? watchAdTask.completedCount : 0,
    watchAdLimit: watchAdTask ? watchAdTask.dailyLimit : 0,
  };
}

function getTaskByKey(taskKey) {
  return state.tasks.find((task) => task.taskKey === taskKey);
}

function applyTaskReward(taskKey) {
  const task = getTaskByKey(taskKey);
  if (!task || task.remaining <= 0) {
    return null;
  }

  task.completedCount += 1;
  task.remaining = Math.max(task.dailyLimit - task.completedCount, 0);
  task.completed = task.remaining <= 0;
  state.balance += task.reward;
  state.pointsToday += task.reward;
  render();
  return task;
}

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
  referralReward: getNumber("referralReward", 50),
  supportUrl: getParam("supportUrl", "https://t.me/dailyrichbot"),
  tutorialUrl: getParam("tutorialUrl", "https://youtube.com/watch?v=your_video_id"),
  referralCode: getParam("ref", `start=${Math.random().toString(36).slice(2, 9)}`),
  tasks: [],
  referralUsers: getJson("referralUsers", []),
  withdrawals: getJson("withdrawals", []),
  withdrawEnabled: getParam("withdrawEnabled", "0") === "1",
  minWithdrawBdt: getNumber("minWithdrawBdt", 500),
  minActiveReferrals: getNumber("minActiveReferrals", 10),
  apiBase: getParam("apiBase", defaultApiBase),
  withdrawState: null,
};

state.tasks = (getJson("tasks", []) || []).map(normalizeTask);
if (!state.tasks.length) {
  state.tasks = buildFallbackTasks(state.adsLimit).map(normalizeTask);
}

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
  submitWithdrawButton: document.getElementById("submitWithdrawButton"),
  withdrawMethodSelect: document.getElementById("withdrawMethodSelect"),
  withdrawNumberInput: document.getElementById("withdrawNumberInput"),
  withdrawReqInfo: document.getElementById("withdrawReqInfo"),
  withdrawReqBadge: document.getElementById("withdrawReqBadge"),
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
  const stats = getTaskStats();
  const initial = state.name.trim().charAt(0).toUpperCase() || "D";
  els.avatarInitial.textContent = initial;
  els.miniAvatarInitial.textContent = initial;
  els.displayName.textContent = `Hi, ${state.name} 👋`;
  els.balanceValue.textContent = `BDT ${currency.format(state.balance)}`;
  els.tasksBalanceValue.textContent = formatMoney(state.balance);
  els.walletBalanceValue.textContent = formatMoney(state.balance);
  els.adsToday.textContent = `${stats.watchAdCompleted} / ${stats.watchAdLimit}`;
  els.referralsCount.textContent = String(state.referrals);
  els.homeTasksCompleted.textContent = String(stats.totalCompleted);
  els.goalsCounter.textContent = `${stats.totalCompleted} / ${stats.totalLimit}`;
  const progressPercent = stats.totalLimit > 0
    ? Math.min((stats.totalCompleted / stats.totalLimit) * 100, 100)
    : 0;
  els.goalProgressFill.style.width = `${Math.max(progressPercent, 0)}%`;
  els.goalHelperText.textContent = `You have ${stats.remainingTotal} tasks remaining today`;
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
  els.taskListContainer.innerHTML = state.tasks.map((task, index) => {
    const taskCompleted = task.remaining <= 0;
    const remainingToday = task.remaining;
    const badge = taskCompleted
      ? "Completed"
      : task.kind === "instant"
        ? "Instant"
        : task.taskKey === "watch_ad"
          ? "Play"
          : task.taskKey === "visit_site"
            ? "Visit"
            : "Task";
    const cardClass = taskCompleted ? "task-card task-card-muted" : (index === 0 ? "task-card task-card-primary" : "task-card");
    const rewardClass = taskCompleted ? "reward-pill reward-pill-muted" : "reward-pill reward-pill-green";
    const buttonClass = taskCompleted ? "primary-button disabled-button" : (index % 2 === 0 ? "primary-button" : "primary-button alt-button");
    const buttonLabel = taskCompleted ? "Completed" : escapeHtml(task.buttonText || "Open Task");
    const actionName = task.kind === "instant"
      ? "instant-task"
      : (task.taskKey === "watch_ad"
        ? "watch-ad"
        : (task.taskKey === "visit_site" ? "visit-site" : "open-task-link"));
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
        <button class="${buttonClass}" ${taskCompleted ? "disabled" : ""} data-action="${actionName}" data-task-key="${escapeHtml(task.taskKey)}" data-task-url="${escapeHtml(task.url || "")}" type="button">${buttonLabel}</button>
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

function renderWithdrawRequestState(data) {
  if (!els.withdrawReqInfo || !els.withdrawReqBadge || !els.submitWithdrawButton) {
    return;
  }

  if (!data) {
    els.withdrawReqBadge.textContent = "Unavailable";
    els.withdrawReqInfo.textContent = "Cannot load withdrawal eligibility right now.";
    els.submitWithdrawButton.disabled = true;
    return;
  }

  const lines = [
    `Balance: ${Number(data.balance_bdt || 0).toFixed(2)} BDT`,
    `Active referrals: ${data.active_referrals || 0}/${data.min_active_referrals || state.minActiveReferrals}`,
    `Minimum withdrawal: ${data.min_withdrawal_bdt || state.minWithdrawBdt} BDT`,
  ];

  if (data.has_pending_withdrawal) {
    lines.push("You already have a pending withdrawal request.");
  }
  if (data.missing_points > 0) {
    lines.push(`Need ${data.missing_points} more points.`);
  }
  if (data.missing_referrals > 0) {
    lines.push(`Need ${data.missing_referrals} more active referrals.`);
  }

  els.withdrawReqInfo.innerHTML = lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
  els.withdrawReqBadge.textContent = data.can_withdraw ? "Eligible" : "Not Eligible";
  els.submitWithdrawButton.disabled = !data.can_withdraw;
}

async function miniApiPost(path, payload) {
  const res = await fetch(`${state.apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({ error: res.statusText }));
  if (!res.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

async function loadWithdrawRequestState() {
  if (!els.withdrawReqInfo || !els.withdrawReqBadge) {
    return;
  }

  if (!tg?.initData) {
    state.withdrawState = null;
    els.withdrawReqBadge.textContent = "Telegram Required";
    els.withdrawReqInfo.textContent = "Open the mini app from Telegram to submit withdrawal request.";
    if (els.submitWithdrawButton) {
      els.submitWithdrawButton.disabled = true;
    }
    return;
  }

  els.withdrawReqBadge.textContent = "Checking...";
  els.withdrawReqInfo.textContent = "Loading eligibility...";
  if (els.submitWithdrawButton) {
    els.submitWithdrawButton.disabled = true;
  }

  try {
    const data = await miniApiPost("/api/mini/withdrawal_state", { init_data: tg.initData });
    state.withdrawState = data;
    renderWithdrawRequestState(data);
  } catch (error) {
    state.withdrawState = null;
    renderWithdrawRequestState(null);
    popup("Withdrawal", error.message || "Failed to load withdrawal status.");
  }
}

async function submitWithdrawRequest() {
  if (!state.withdrawEnabled) {
    popup("Withdrawal", "Withdrawal is currently disabled.");
    return;
  }

  if (!tg?.initData) {
    popup("Withdrawal", "Open mini app from Telegram to submit request.");
    return;
  }

  const method = els.withdrawMethodSelect?.value?.trim();
  const number = (els.withdrawNumberInput?.value || "").trim();
  if (!method || !["bkash", "nagad", "rocket"].includes(method)) {
    popup("Withdrawal", "Select a valid payment method.");
    return;
  }

  if (!(number.length === 11 && number.startsWith("01") && /^\d+$/.test(number))) {
    popup("Withdrawal", "Enter valid personal number (01XXXXXXXXX).");
    return;
  }

  try {
    const result = await miniApiPost("/api/mini/withdraw", {
      init_data: tg.initData,
      payment_method: method,
      payment_number: number,
    });

    if (result.wallet_state) {
      state.withdrawState = result.wallet_state;
      state.balance = Number(result.wallet_state.balance_bdt || 0);
    }

    if (result.withdrawal) {
      state.withdrawals.unshift({
        amount: Number(result.withdrawal.amount || 0),
        status: result.withdrawal.status || "pending",
        method: result.withdrawal.method || method,
        date: new Date().toISOString().slice(0, 10),
      });
    }

    render();
    renderWithdrawRequestState(state.withdrawState);
    if (els.withdrawNumberInput) {
      els.withdrawNumberInput.value = "";
    }
    popup("Success", "Withdrawal request submitted successfully.");
    activateScreen("wallet");
  } catch (error) {
    popup("Withdrawal", error.message || "Failed to submit withdrawal request.");
    await loadWithdrawRequestState();
  }
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

function handleAction(action, explicitTarget, taskKey, taskUrl) {
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
    const task = getTaskByKey(taskKey || "watch_ad");
    if (!task || task.remaining <= 0) {
      popup("Limit Reached", "আজকের জন্য এই টাস্কের সীমা শেষ হয়ে গেছে।");
      return;
    }
    if (typeof show_10728950 !== "function") {
      popup("Please Wait", "Ad network লোড হচ্ছে। একটু পর আবার চেষ্টা করুন।");
      return;
    }
    // Rewarded Interstitial
    show_10728950().then(() => {
      const rewardedTask = applyTaskReward(task.taskKey);
      if (!rewardedTask) {
        popup("Limit Reached", "আজকের জন্য এই টাস্কের সীমা শেষ হয়ে গেছে।");
        return;
      }
      render();
      popup("Reward Earned! 🎉", `আপনি ${rewardedTask.reward.toFixed(2)} BDT পুরস্কার পেয়েছেন ${rewardedTask.title} সম্পন্ন করার জন্য!`);
    });
    return;
  }

  if (action === "instant-task") {
    const task = applyTaskReward(taskKey);
    if (!task) {
      popup("Task Completed", "এই টাস্কের আজকের সীমা শেষ হয়ে গেছে।");
      return;
    }
    popup("Reward Earned! 🎉", `আপনি ${task.reward.toFixed(2)} BDT পুরস্কার পেয়েছেন ${task.title} সম্পন্ন করার জন্য!`);
    return;
  }

  if (action === "visit-site") {
    const task = getTaskByKey(taskKey || "visit_site");
    if (!task || task.remaining <= 0) {
      popup("Limit Reached", "আজকের জন্য এই টাস্কের সীমা শেষ হয়ে গেছে।");
      return;
    }
    if (typeof show_10728950 !== "function") {
      popup("Please Wait", "Ad network লোড হচ্ছে। একটু পর আবার চেষ্টা করুন।");
      return;
    }
    // Rewarded Popup
    show_10728950("pop").then(() => {
      const rewardedTask = applyTaskReward(task.taskKey);
      if (!rewardedTask) {
        popup("Limit Reached", "আজকের জন্য এই টাস্কের সীমা শেষ হয়ে গেছে।");
        return;
      }
      render();
      popup("Reward Earned! 🎉", `আপনি ${rewardedTask.reward.toFixed(2)} BDT পুরস্কার পেয়েছেন ${rewardedTask.title} সম্পন্ন করার জন্য!`);
    }).catch(() => {
      // user closed or error — no reward, do nothing
    });
    return;
  }

  if (action === "open-task-link") {
    const task = getTaskByKey(taskKey);
    if (!task) {
      popup("Task Error", "এই টাস্কটি খুঁজে পাওয়া যায়নি।");
      return;
    }
    if (task.remaining <= 0) {
      popup("Limit Reached", "আজকের জন্য এই টাস্কের সীমা শেষ হয়ে গেছে।");
      return;
    }
    if (taskUrl) {
      window.open(taskUrl, "_blank", "noopener,noreferrer");
    }
    const rewardedTask = applyTaskReward(task.taskKey);
    if (!rewardedTask) {
      popup("Task Completed", "এই টাস্কের আজকের সীমা শেষ হয়ে গেছে।");
      return;
    }
    popup("Reward Earned! 🎉", `আপনি ${rewardedTask.reward.toFixed(2)} BDT পুরস্কার পেয়েছেন ${rewardedTask.title} সম্পন্ন করার জন্য!`);
    return;
  }

  if (action === "withdraw") {
    activateScreen("withdraw-request");
    loadWithdrawRequestState();
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
  if (!document.body.dataset.actionsBound) {
    document.body.dataset.actionsBound = "1";
    document.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) {
        return;
      }
      handleAction(
        button.dataset.action,
        button.dataset.target,
        button.dataset.taskKey,
        button.dataset.taskUrl,
      );
    });
  }

  els.copyReferralButton.addEventListener("click", () => handleAction("copy-referral"));
  els.shareReferralButton.addEventListener("click", () => handleAction("share-referral"));
  if (els.tutorialButton) {
    els.tutorialButton.addEventListener("click", () => handleAction("tutorial"));
  }
  els.withdrawButton.addEventListener("click", () => handleAction("withdraw"));
  if (els.submitWithdrawButton) {
    els.submitWithdrawButton.addEventListener("click", submitWithdrawRequest);
  }
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
