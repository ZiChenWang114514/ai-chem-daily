const page = document.body.dataset.page || "home";
const channelId = document.body.dataset.channel || "";
const root = document.body.dataset.root || "";
const state = {
  payload: null,
  manifest: null,
  activity: [],
  activityMetric: "selected",
  source: "all",
  query: "",
};
const channelNames = {
  aixchem: "AI × Chem",
  aixbio: "AI × Bio",
  aixmath: "AI × Math",
  aivoices: "AI Voices",
  engineering: "Engineering",
};
const channelTitles = {
  aixchem: "化学",
  aixbio: "生命科学",
  aixmath: "数学",
  aivoices: "公开观点",
  engineering: "工程更新",
};
const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];

function path(value) {
  return `${root}${value}`;
}

function requestedDate() {
  return new URLSearchParams(location.search).get("date") || "";
}

function viewingHistory() {
  return Boolean(requestedDate());
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value ?? "—";
}

function formatDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${year} 年 ${Number(month)} 月 ${Number(day)} 日`;
}

function weekdayLabel(value) {
  if (!value) return "";
  const [year, month, day] = value.split("-").map(Number);
  return weekdays[new Date(year, month - 1, day).getDay()] || "";
}

function formatGeneratedAt(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.valueOf())) return "生成时间暂缺";
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const read = (type) => parts.find((part) => part.type === type)?.value || "";
  return `${read("month")} 月 ${read("day")} 日 ${read("hour")}:${read("minute")} 更新`;
}

function dateKey(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

function dateFromKey(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function withDate(href, date) {
  if (!date) return href;
  const glue = href.includes("?") ? "&" : "?";
  return `${href}${glue}date=${encodeURIComponent(date)}`;
}

function activityLevel(value, maximum) {
  if (!value || !maximum) return 0;
  return Math.max(1, Math.min(4, Math.ceil(Math.sqrt(value / maximum) * 4)));
}

function payloadItems(payload = state.payload) {
  return payload?.items || payload?.papers || [];
}

function currentDate() {
  return requestedDate() || state.payload?.date || "";
}

function friendlySourceNote(errors) {
  const names = [...new Set((errors || []).map((item) => String(item).split(":")[0].trim()).filter(Boolean))];
  if (!names.length) return "";
  return `部分来源今日暂不可用：${names.join("、")}`;
}

function displayTitle(item) {
  const title = (item.title || "").trim();
  const repo = item.metadata?.repository || "";
  const version = item.metadata?.version || "";
  if (repo && version && (!title || /^b\d+$/i.test(title) || title === version)) {
    return `${repo.split("/").pop()} ${version}`;
  }
  return title || "未命名条目";
}

function sameText(left, right) {
  return String(left || "").replace(/\s+/g, "") === String(right || "").replace(/\s+/g, "");
}

function renderHeatmap() {
  const container = document.getElementById("activity-heatmap");
  if (!container) return;
  container.replaceChildren();
  const relevant = state.activity.filter((item) => page === "home" || item.channel === channelId);
  const byDate = new Map();
  relevant.forEach((item) => {
    const existing = byDate.get(item.date) || { date: item.date, fetched: 0, candidates: 0, selected: 0 };
    ["fetched", "candidates", "selected"].forEach((metric) => {
      existing[metric] += Number(item[metric]) || 0;
    });
    byDate.set(item.date, existing);
  });
  const metric = state.activityMetric;
  const dates = [...byDate.keys()].sort();
  const latestDate = dates.at(-1) || state.payload?.date || dateKey(new Date());
  const firstDate = dates[0] || latestDate;
  const maximum = Math.max(0, ...[...byDate.values()].map((item) => item[metric] || 0));
  const end = dateFromKey(latestDate);
  end.setUTCDate(end.getUTCDate() + (6 - end.getUTCDay()));
  const start = dateFromKey(firstDate);
  start.setUTCDate(start.getUTCDate() - start.getUTCDay());
  const dayCount = Math.round((end - start) / 86400000) + 1;
  let previousMonth = -1;
  let populatedDays = 0;
  let total = 0;
  const viewing = currentDate();

  ["日", "一", "二", "三", "四", "五", "六"].forEach((label) => {
    const dow = document.createElement("span");
    dow.className = "heatmap__dow";
    dow.textContent = label;
    container.appendChild(dow);
  });

  for (let offset = 0; offset < dayCount; offset += 1) {
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
    const cell = document.createElement(item ? "button" : "span");
    cell.className = "heatmap__day";
    cell.dataset.level = activityLevel(value, maximum);
    cell.setAttribute("role", "gridcell");
    const label = `${formatDate(key)}：精选 ${value}`;
    cell.title = label;
    cell.setAttribute("aria-label", label);
    if (key === viewing) cell.classList.add("is-current");
    if (item) {
      cell.type = "button";
      cell.addEventListener("click", () => {
        location.href = `?date=${encodeURIComponent(key)}`;
      });
    }
    container.appendChild(cell);
    if (value > 0) populatedDays += 1;
    total += value;
  }
  setText("activity-summary", `有记录 ${populatedDays} 天，合计 ${total.toLocaleString("zh-CN")} 项精选`);
  const scroller = container.closest(".heatmap-scroll");
  if (scroller) scroller.scrollLeft = scroller.scrollWidth;
}

function renderChannels() {
  const container = document.getElementById("channel-cards");
  if (!container || !state.manifest) return;
  container.replaceChildren();
  const date = requestedDate();
  state.manifest.channels.forEach((channel) => {
    const dailyChannel = state.payload?.channels?.find((item) => item.id === channel.id);
    const selected = dailyChannel
      ? Number(dailyChannel.stats?.selected ?? (dailyChannel.items || []).length ?? 0)
      : date
        ? 0
        : Number(channel.stats?.selected || 0);
    const card = document.createElement("a");
    card.className = "channel-card";
    card.href = withDate(path(`channels/${channel.id}/`), date);
    card.style.setProperty("--channel-accent", channel.accent || "#1b7d76");

    const art = document.createElement("img");
    art.className = "channel-card__art";
    art.src = path(`assets/art/${channel.id}.jpg`);
    art.alt = "";
    art.loading = "lazy";

    const body = document.createElement("div");
    body.className = "channel-card__body";
    const top = document.createElement("div");
    top.className = "channel-card__top";
    const icon = document.createElement("img");
    icon.className = "channel-card__icon";
    icon.src = path(`assets/icons/${channel.id}.svg`);
    icon.alt = "";
    const title = document.createElement("h3");
    title.textContent = channel.name;
    const count = document.createElement("span");
    count.className = selected > 0 ? "channel-card__count" : "channel-card__count is-empty";
    count.textContent = selected > 0 ? `${selected} 项` : "暂无";
    top.append(icon, title, count);

    const description = document.createElement("p");
    description.textContent = channel.description;
    const meta = document.createElement("span");
    meta.className = "channel-card__meta";
    meta.textContent = (channel.sources || []).slice(0, 3).join(" · ");
    body.append(top, description, meta);
    card.append(art, body);
    container.appendChild(card);
  });
}

function paperSearchText(item) {
  return [
    displayTitle(item),
    item.abstract_or_text,
    item.abstract,
    item.author_line,
    ...(item.creators || []),
    item.source,
    item.category,
    ...(item.tags || []),
  ].join(" ").toLocaleLowerCase("zh-CN");
}

function visibleItems() {
  const query = state.query.trim().toLocaleLowerCase("zh-CN");
  return payloadItems().filter((item) => (
    (state.source === "all" || item.source === state.source)
    && (!query || paperSearchText(item).includes(query))
  ));
}

function createItemCard(item, groupName) {
  const fragment = document.getElementById("paper-template").content.cloneNode(true);
  fragment.querySelector(".rank").textContent = String(item.rank || 0).padStart(2, "0");
  fragment.querySelector(".source-badge").textContent = item.source;
  const topic = fragment.querySelector(".topic-label");
  if (!item.category || item.category === groupName) topic.remove();
  else topic.textContent = item.category;
  const title = fragment.querySelector(".paper-title");
  title.href = item.url;
  title.textContent = displayTitle(item);
  const creators = item.author_line || (item.creators || []).slice(0, 3).join(", ") || "作者信息暂缺";
  fragment.querySelector(".paper-meta").textContent = `${creators} · ${(item.published_at || item.published || "日期暂缺").slice(0, 10)}`;
  const summary = item.summary_zh || "中文说明暂缺，请查看原始内容。";
  fragment.querySelector(".summary-zh").textContent = summary;
  const why = fragment.querySelector(".why-it-matters");
  if (item.why_it_matters_zh && !sameText(item.why_it_matters_zh, item.summary_zh)) {
    why.textContent = item.why_it_matters_zh;
  } else {
    why.remove();
  }
  fragment.querySelector(".abstract-text").textContent = item.abstract_or_text || item.abstract || "该来源未提供摘要或正文。";
  const tags = fragment.querySelector(".tag-list");
  [...new Set(item.tags || [])]
    .filter((tag) => tag && tag !== item.category && tag !== item.source)
    .slice(0, 6)
    .forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = tag;
      tags.appendChild(span);
    });
  return fragment;
}

function emptyDayText() {
  const weekday = weekdayLabel(state.payload?.date);
  if (weekday === "星期日") return "星期日预印本源站通常没有新记录。可在上方打开历史日报。";
  return "这一天没有达到收录标准的更新。可在上方打开历史日报。";
}

function renderEmptyState(filteredCount) {
  const empty = document.getElementById("empty-state");
  const toolbar = document.querySelector(".toolbar");
  const allCount = payloadItems().length;
  empty.hidden = filteredCount > 0;
  if (toolbar) toolbar.hidden = allCount === 0;
  if (filteredCount > 0) return;
  if (allCount === 0) {
    setText("empty-title", viewingHistory() ? "当日暂无精选" : "今日暂无精选");
    setText("empty-text", emptyDayText());
    return;
  }
  setText("empty-title", "没有匹配的内容");
  setText("empty-text", "请减少筛选条件或更换搜索词。");
}

function renderItems() {
  const items = visibleItems();
  const container = document.getElementById("paper-groups");
  container.replaceChildren();
  const total = payloadItems().length;
  setText("result-count", total ? `显示 ${items.length} / ${total} 项` : "");
  renderEmptyState(items.length);
  const groups = new Map();
  items.forEach((item) => {
    const group = item.category || (page === "home" ? "其他更新" : "当日收录");
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(item);
  });
  groups.forEach((values, name) => {
    const section = document.createElement("section");
    section.className = "paper-group";
    const title = document.createElement("h3");
    title.className = "group-title";
    title.append(document.createTextNode(name));
    const count = document.createElement("span");
    count.textContent = `${values.length} 项`;
    title.appendChild(count);
    section.appendChild(title);
    values.forEach((item) => section.appendChild(createItemCard(item, name)));
    container.appendChild(section);
  });
}

function renderSourceFilters() {
  const container = document.getElementById("source-filters");
  container.replaceChildren();
  const sources = ["all", ...new Set(payloadItems().map((item) => item.source).filter(Boolean))];
  sources.forEach((source) => {
    const button = document.createElement("button");
    button.className = `filter-chip${source === state.source ? " is-active" : ""}`;
    button.type = "button";
    button.dataset.source = source;
    button.textContent = source === "all" ? "全部来源" : source;
    container.appendChild(button);
  });
}

function markChannelNav() {
  const date = requestedDate();
  document.querySelectorAll(".channel-nav__item").forEach((link) => {
    const href = link.getAttribute("href") || "";
    const isOverview = link.textContent.trim() === "总览";
    const active = page === "channel" ? href.includes(`/${channelId}`) || href.includes(`${channelId}/`) : isOverview;
    link.classList.toggle("is-active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
    if (!date) return;
    const base = href.split("?")[0];
    link.href = withDate(base, date);
  });
}

function renderHero(payload) {
  const isHome = page === "home";
  const date = payload.date || "";
  const history = viewingHistory();
  document.title = isHome
    ? `AIX Daily · ${date}`
    : `${channelNames[channelId] || "AIX Daily"} · ${date}`;
  setText("digest-date", formatDate(date));
  const dateNode = document.getElementById("digest-date");
  if (dateNode) dateNode.dateTime = date;
  setText("hero-weekday", weekdayLabel(date));
  setText("eyebrow", isHome ? (history ? "历史日报" : "今日精选") : (channelNames[channelId] || "频道"));
  const title = document.getElementById("hero-title");
  if (title) {
    title.textContent = isHome
      ? (history ? "这一天的研究更新" : "五个频道的研究更新")
      : (channelTitles[channelId] || channelNames[channelId] || payload.title || "每日精选");
  }
  setText("papers-title", history ? "当日内容" : "今日内容");
  const back = document.getElementById("back-to-today");
  if (back) {
    back.hidden = !history;
    back.href = page === "home" ? path("./") : "./";
  }
  setText("subtitle", isHome ? (payload.overview_zh || "") : (payload.subtitle || payload.overview_zh || ""));
  setText("generated-time", formatGeneratedAt(payload.generated_at));
  const stats = isHome
    ? (payload.channels || []).reduce((acc, channel) => acc + Number(channel.stats?.selected || 0), 0)
    : payload.stats?.selected || payloadItems(payload).length;
  setText("stat-selected", Number(stats).toLocaleString("zh-CN"));
  setText("footer-date", date ? `${history ? "本期日期" : "最近更新"}：${formatDate(date)}` : "—");

  const art = document.getElementById("hero-art");
  if (art) art.src = path(isHome ? "assets/art/hero.jpg" : `assets/art/${channelId}.jpg`);

  const note = document.getElementById("source-note");
  const errors = isHome
    ? (payload.channels || []).flatMap((channel) => channel.source_errors || [])
    : payload.source_errors || [];
  const message = friendlySourceNote(errors);
  if (note) {
    note.hidden = !message;
    note.textContent = message;
  }
}

function renderPayload(payload) {
  state.payload = payload;
  renderHero(payload);
  renderChannels();
  renderSourceFilters();
  renderItems();
  renderHeatmap();
  markChannelNav();
}

function markHomeOnlySections() {
  document.querySelectorAll("[data-home-only]").forEach((element) => {
    element.hidden = page !== "home";
  });
}

async function loadManifestAndActivity() {
  const [manifestResponse, activityResponse] = await Promise.all([
    fetch(path("api/v1/manifest.json"), { cache: "no-store" }),
    fetch(path("api/v1/activity.json"), { cache: "no-store" }),
  ]);
  if (!manifestResponse.ok || !activityResponse.ok) throw new Error("公共接口暂时不可用");
  state.manifest = await manifestResponse.json();
  state.activity = (await activityResponse.json()).items || [];
  renderChannels();
  renderHeatmap();
  markChannelNav();
}

function groupedHistory(items) {
  const byDate = new Map();
  items.forEach((item) => {
    const existing = byDate.get(item.date) || { date: item.date, selected: 0 };
    existing.selected += Number(item.selected) || 0;
    byDate.set(item.date, existing);
  });
  return [...byDate.values()].sort((left, right) => right.date.localeCompare(left.date));
}

async function loadArchive() {
  const container = document.getElementById("history-list");
  const archivePath = page === "channel" ? `data/channels/${channelId}/archive/index.json` : "api/v1/activity.json";
  try {
    const response = await fetch(path(archivePath), { cache: "no-store" });
    const value = await response.json();
    const items = page === "channel" ? value.items || [] : groupedHistory(value.items || []);
    const viewing = currentDate();
    container.replaceChildren();
    items.forEach((item) => {
      const link = document.createElement("a");
      link.className = "history-link";
      if (item.date === viewing) {
        link.classList.add("is-current");
        link.setAttribute("aria-current", "page");
      }
      link.href = `?date=${encodeURIComponent(item.date)}`;
      link.append(document.createTextNode(formatDate(item.date)));
      const count = document.createElement("span");
      count.textContent = `${item.selected || 0} 项精选`;
      link.appendChild(count);
      container.appendChild(link);
    });
  } catch (error) {
    container.textContent = `历史列表读取失败：${error.message}`;
  }
}

function flattenHomeItems(payload) {
  let rank = 0;
  payload.items = (payload.channels || []).flatMap((channel) => (
    (channel.items || channel.papers || []).map((item) => {
      rank += 1;
      return { ...item, rank, category: channel.name };
    })
  ));
  return payload;
}

async function loadHomeDigest(date) {
  const url = date ? `data/daily/archive/${encodeURIComponent(date)}.json` : "data/daily/latest.json";
  const response = await fetch(path(url), { cache: "no-store" });
  if (!response.ok) throw new Error(date ? `没有 ${date} 的综合日报` : `HTTP ${response.status}`);
  return flattenHomeItems(await response.json());
}

async function loadDigest() {
  const date = requestedDate();
  const payload = page === "home"
    ? await loadHomeDigest(date)
    : await (async () => {
      const url = date
        ? `data/channels/${channelId}/archive/${encodeURIComponent(date)}.json`
        : `data/channels/${channelId}/latest.json`;
      const response = await fetch(path(url), { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })();
  renderPayload(payload);
  loadArchive();
}

function bindEvents() {
  document.getElementById("search-input")?.addEventListener("input", (event) => {
    state.query = event.target.value;
    renderItems();
  });
  document.getElementById("source-filters")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-source]");
    if (!button) return;
    state.source = button.dataset.source;
    document.querySelectorAll("button[data-source]").forEach((item) => item.classList.toggle("is-active", item === button));
    renderItems();
  });
  const historyButton = document.getElementById("history-button");
  const historyPanel = document.getElementById("history-panel");
  const closeHistory = () => {
    if (!historyButton || !historyPanel) return;
    historyButton.setAttribute("aria-expanded", "false");
    historyPanel.hidden = true;
  };
  historyButton?.addEventListener("click", () => {
    const open = historyButton.getAttribute("aria-expanded") === "true";
    historyButton.setAttribute("aria-expanded", String(!open));
    historyPanel.hidden = open;
  });
  document.addEventListener("click", (event) => {
    if (!historyPanel || historyPanel.hidden) return;
    if (historyPanel.contains(event.target) || historyButton.contains(event.target)) return;
    closeHistory();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeHistory();
  });
}

function showLoadError(error) {
  const container = document.getElementById("paper-groups");
  if (!container) return;
  container.replaceChildren();
  const box = document.createElement("div");
  box.className = "empty-state";
  const title = document.createElement("strong");
  title.textContent = "日报数据暂时无法读取";
  const text = document.createElement("p");
  text.textContent = error.message;
  box.append(title, text);
  container.appendChild(box);
}

markHomeOnlySections();
bindEvents();
Promise.all([loadManifestAndActivity(), loadDigest()]).catch(showLoadError);
