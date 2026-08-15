const state = {
  payload: null,
  manifest: null,
  archive: [],
  activity: [],
  activityMetric: "selected",
  source: "all",
  query: "",
};

const groupOrder = ["今日精选", "方法与模型", "分子与药物发现", "结构与生物", "材料与催化"];

function formatDate(value) {
  if (!value) return "—";
  const parts = value.split("-");
  if (parts.length !== 3) return value;
  return `${parts[0]} 年 ${Number(parts[1])} 月 ${Number(parts[2])} 日`;
}

function formatGeneratedAt(value) {
  if (!value) return "生成时间暂缺";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return `生成于 ${new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date)}（北京时间）`;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value ?? "—";
}

function dateKey(date) {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateFromKey(value) {
  const [year, month, day] = String(value).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function activityLevel(value, maximum) {
  if (!value || !maximum) return 0;
  const ratio = Math.sqrt(value / maximum);
  return Math.max(1, Math.min(4, Math.ceil(ratio * 4)));
}

function renderHeatmap() {
  const container = document.getElementById("activity-heatmap");
  if (!container) return;
  container.replaceChildren();
  const metric = state.activityMetric;
  const byDate = new Map(
    state.activity
      .filter((item) => item.channel === "aixchem")
      .map((item) => [item.date, item])
  );
  const values = [...byDate.values()].map((item) => Number(item[metric]) || 0);
  const maximum = Math.max(0, ...values);
  const activityDates = state.activity.map((item) => item.date).filter(Boolean).sort();
  const latestDate = activityDates.at(-1) || state.payload?.date || dateKey(new Date());
  const end = dateFromKey(latestDate);
  end.setUTCDate(end.getUTCDate() + (6 - end.getUTCDay()));
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 370);
  const activeDate = new URLSearchParams(location.search).get("date") || state.payload?.date;
  const metricNames = { selected: "精选", candidates: "候选", fetched: "抓取" };
  let populatedDays = 0;
  let total = 0;
  let previousMonth = -1;

  for (let offset = 0; offset < 371; offset += 1) {
    const day = new Date(start);
    day.setUTCDate(start.getUTCDate() + offset);
    const key = dateKey(day);
    const item = byDate.get(key);
    const value = Number(item?.[metric]) || 0;
    const week = Math.floor(offset / 7);
    if (day.getUTCMonth() !== previousMonth && (offset === 0 || day.getUTCDate() <= 7)) {
      previousMonth = day.getUTCMonth();
      const month = document.createElement("span");
      month.className = "heatmap__month";
      month.style.setProperty("--week", week);
      month.textContent = `${day.getUTCMonth() + 1}月`;
      container.appendChild(month);
    }

    const hasArchive = Boolean(item?.href);
    const cell = document.createElement(hasArchive ? "button" : "span");
    cell.className = "heatmap__day";
    cell.dataset.level = String(activityLevel(value, maximum));
    cell.setAttribute("role", "gridcell");
    if (key > latestDate) cell.classList.add("is-future");
    if (key === activeDate) cell.classList.add("is-current");
    const label = `${formatDate(key)}：${metricNames[metric]} ${value.toLocaleString("zh-CN")}`;
    cell.title = label;
    cell.setAttribute("aria-label", label);
    if (hasArchive) {
      cell.type = "button";
      cell.addEventListener("click", () => {
        location.href = item.kind === "html" ? item.href : `?date=${encodeURIComponent(key)}`;
      });
    }
    container.appendChild(cell);
    if (value > 0) populatedDays += 1;
    total += value;
  }
  const units = { selected: "篇精选", candidates: "篇候选", fetched: "条抓取记录" };
  setText("activity-summary", `过去一年有 ${populatedDays} 天记录，共计 ${total.toLocaleString("zh-CN")} ${units[metric]}`);
}

function renderChannels() {
  const container = document.getElementById("channel-cards");
  if (!container || !state.manifest) return;
  container.replaceChildren();
  state.manifest.channels.forEach((channel) => {
    const card = document.createElement("article");
    card.className = `channel-card ${channel.status === "active" ? "is-active" : ""}`;
    card.style.setProperty("--channel-accent", channel.accent || "#0d7c78");
    const top = document.createElement("div");
    top.className = "channel-card__top";
    const title = document.createElement("h3");
    title.textContent = channel.name;
    const status = document.createElement("span");
    status.className = "channel-card__status";
    status.textContent = channel.status === "active" ? "每日更新" : (channel.has_data ? "已有资料" : "待接入");
    top.append(title, status);
    const description = document.createElement("p");
    description.textContent = channel.description;
    const meta = document.createElement("span");
    meta.className = "channel-card__meta";
    meta.textContent = channel.status === "active" || channel.has_data
      ? `最近一期 ${channel.latest_date || "等待生成"}`
      : `拟接入：${(channel.sources || []).join(" · ")}`;
    card.append(top, description, meta);
    container.appendChild(card);
  });
}

function paperSearchText(paper) {
  return [paper.title, paper.abstract, paper.author_line, paper.source, paper.category, ...(paper.tags || [])]
    .join(" ")
    .toLocaleLowerCase("zh-CN");
}

function visiblePapers() {
  if (!state.payload) return [];
  const query = state.query.trim().toLocaleLowerCase("zh-CN");
  return state.payload.papers.filter((paper) => {
    const sourceMatches = state.source === "all" || paper.source === state.source;
    const queryMatches = !query || paperSearchText(paper).includes(query);
    return sourceMatches && queryMatches;
  });
}

function createPaperCard(paper) {
  const template = document.getElementById("paper-template");
  const fragment = template.content.cloneNode(true);
  const article = fragment.querySelector("article");
  article.dataset.source = paper.source;
  fragment.querySelector(".rank").textContent = String(paper.rank).padStart(2, "0");
  fragment.querySelector(".source-badge").textContent = paper.source;
  fragment.querySelector(".topic-label").textContent = paper.featured ? "★ 今日精选" : paper.category;
  fragment.querySelector(".score-label").textContent = `综合评分 ${Math.round(paper.quality_score || 0)}`;
  const title = fragment.querySelector(".paper-title");
  title.href = paper.url;
  title.textContent = paper.title;
  fragment.querySelector(".paper-meta").textContent = `${paper.author_line || "作者信息暂缺"} · ${paper.published || "日期暂缺"}`;
  fragment.querySelector(".summary-zh").textContent = paper.summary_zh || "中文说明暂缺，请查看英文摘要。";
  fragment.querySelector(".why-it-matters").textContent = paper.why_it_matters_zh || "请结合原文判断研究价值。";
  fragment.querySelector(".abstract-text").textContent = paper.abstract || "该数据源未提供摘要。";
  const tagList = fragment.querySelector(".tag-list");
  [...new Set(paper.tags || [])].slice(0, 6).forEach((tag) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag;
    tagList.appendChild(span);
  });
  return fragment;
}

function renderPapers() {
  const papers = visiblePapers();
  const container = document.getElementById("paper-groups");
  const empty = document.getElementById("empty-state");
  container.replaceChildren();
  empty.hidden = papers.length > 0;
  setText("result-count", `显示 ${papers.length} / ${state.payload?.papers?.length || 0} 篇`);

  const groups = new Map();
  papers.forEach((paper) => {
    const group = paper.featured ? "今日精选" : (paper.category || "方法与模型");
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(paper);
  });

  groupOrder.forEach((name) => {
    const items = groups.get(name);
    if (!items?.length) return;
    const section = document.createElement("section");
    section.className = "paper-group";
    const title = document.createElement("h3");
    title.className = "group-title";
    title.append(document.createTextNode(name));
    const count = document.createElement("span");
    count.textContent = `${items.length} 篇`;
    title.appendChild(count);
    section.appendChild(title);
    items.forEach((paper) => section.appendChild(createPaperCard(paper)));
    container.appendChild(section);
  });
}

function renderPayload(payload) {
  state.payload = payload;
  document.title = `${payload.title || "AI × Chem 每日预印本精选"} · ${payload.date || ""}`;
  setText("subtitle", payload.subtitle);
  setText("digest-date", formatDate(payload.date));
  document.getElementById("digest-date").dateTime = payload.date || "";
  setText("window-text", `覆盖 ${payload.window?.start || "—"} 至 ${payload.window?.end || "—"}`);
  setText("generated-time", formatGeneratedAt(payload.generated_at));
  setText("stat-fetched", payload.stats?.fetched?.toLocaleString("zh-CN") || 0);
  setText("stat-candidates", payload.stats?.candidates?.toLocaleString("zh-CN") || 0);
  setText("stat-selected", payload.stats?.selected?.toLocaleString("zh-CN") || 0);
  setText("method-label", payload.method);
  setText("footer-date", `最近更新：${payload.date || "—"}`);

  const note = document.getElementById("method-note");
  const messages = [payload.method_note];
  if (payload.source_errors?.length) {
    messages.push(`本期数据提示：${payload.source_errors.join("；")}`);
    note.classList.add("has-error");
  } else {
    note.classList.remove("has-error");
  }
  note.querySelector("p").textContent = messages.filter(Boolean).join(" ");
  renderPapers();
}

async function loadArchiveIndex() {
  const container = document.getElementById("history-list");
  try {
    const response = await fetch("data/archive/index.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const archive = await response.json();
    container.replaceChildren();
    state.archive = archive.items || [];
    state.archive.forEach((item) => {
      const link = document.createElement("a");
      link.className = "history-link";
      link.href = item.kind === "html" ? item.href : `?date=${encodeURIComponent(item.date)}`;
      link.textContent = formatDate(item.date);
      const count = document.createElement("span");
      count.textContent = item.selected ? `${item.selected} 篇精选` : "历史版本";
      link.appendChild(count);
      container.appendChild(link);
    });
    if (!state.activity.length) {
      state.activity = state.archive.map((item) => ({ ...item, channel: "aixchem" }));
      renderHeatmap();
    }
  } catch (error) {
    container.textContent = `历史列表读取失败：${error.message}`;
  }
}

async function loadHub() {
  try {
    const [manifestResponse, activityResponse] = await Promise.all([
      fetch("api/v1/manifest.json", { cache: "no-store" }),
      fetch("api/v1/activity.json", { cache: "no-store" }),
    ]);
    if (!manifestResponse.ok || !activityResponse.ok) throw new Error("hub interface unavailable");
    state.manifest = await manifestResponse.json();
    const activity = await activityResponse.json();
    state.activity = activity.items || [];
    renderChannels();
    renderHeatmap();
  } catch (_error) {
    renderHeatmap();
  }
}

async function loadDigest() {
  const params = new URLSearchParams(location.search);
  const requestedDate = params.get("date");
  const dataUrl = requestedDate ? `data/archive/${encodeURIComponent(requestedDate)}.json` : "data/latest.json";
  try {
    const response = await fetch(dataUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderPayload(await response.json());
  } catch (error) {
    document.getElementById("paper-groups").innerHTML = `
      <div class="empty-state"><strong>日报数据暂时无法读取</strong><p>${error.message}</p></div>`;
    setText("digest-date", "读取失败");
  }
}

document.getElementById("search-input").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderPapers();
});

document.getElementById("source-filters").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-source]");
  if (!button) return;
  state.source = button.dataset.source;
  document.querySelectorAll("button[data-source]").forEach((item) => item.classList.toggle("is-active", item === button));
  renderPapers();
});

document.getElementById("activity-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-metric]");
  if (!button) return;
  state.activityMetric = button.dataset.metric;
  document.querySelectorAll("#activity-tabs button").forEach((item) => {
    const active = item === button;
    item.classList.toggle("is-active", active);
    item.setAttribute("aria-pressed", String(active));
  });
  renderHeatmap();
});

const historyButton = document.getElementById("history-button");
const historyPanel = document.getElementById("history-panel");
historyButton.addEventListener("click", () => {
  const expanded = historyButton.getAttribute("aria-expanded") === "true";
  historyButton.setAttribute("aria-expanded", String(!expanded));
  historyPanel.hidden = expanded;
});

document.addEventListener("click", (event) => {
  if (historyPanel.hidden || historyPanel.contains(event.target) || historyButton.contains(event.target)) return;
  historyPanel.hidden = true;
  historyButton.setAttribute("aria-expanded", "false");
});

Promise.all([loadDigest(), loadArchiveIndex(), loadHub()]);
