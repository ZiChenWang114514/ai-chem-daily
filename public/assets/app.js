const page = document.body.dataset.page || "home";
const channelId = document.body.dataset.channel || "";
const root = document.body.dataset.root || "";
const state = {
  payload: null,
  manifest: null,
  activity: [],
  archiveDates: new Set(),
  activityMetric: "selected",
  source: "all",
  query: "",
  heatmapSignature: "",
  searchIndex: new WeakMap(),
  libraryTag: "all",
  libraryQuery: "",
  noteTimers: {},
};
const SITE_NAME = "AIX每日精读";
const COLLECTION_KEY = "aix-daily.collection.v1";
const UNTAGGED_LABEL = "未分类";
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
const generatedFormat = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function path(value) {
  return `${root}${value}`;
}

async function loadJSON(url) {
  const response = await fetch(path(url));
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
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
  const parts = generatedFormat.formatToParts(date);
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

function emptyCollection() {
  return { schema_version: 1, updated_at: "", items: {}, notes: {} };
}

function readCollection() {
  try {
    const value = JSON.parse(localStorage.getItem(COLLECTION_KEY) || "");
    if (!value || typeof value.items !== "object" || Array.isArray(value.items)) return emptyCollection();
    if (!value.notes || typeof value.notes !== "object" || Array.isArray(value.notes)) value.notes = {};
    Object.entries(value.items).forEach(([key, item]) => {
      if (item?.note && !value.notes[key]) {
        value.notes[key] = { note: item.note, note_updated_at: item.note_updated_at || "" };
      }
    });
    return value;
  } catch {
    return emptyCollection();
  }
}

function writeCollection(collection) {
  try {
    collection.updated_at = new Date().toISOString();
    localStorage.setItem(COLLECTION_KEY, JSON.stringify(collection));
    updateLibraryBadge();
    return true;
  } catch {
    return false;
  }
}

function collectionItemKey(item) {
  return String(item?.id || item?.url || "").trim();
}

function savedRecord(item) {
  return readCollection().items[collectionItemKey(item)] || null;
}

function recordTags(record) {
  const tags = [];
  if (record.category) tags.push(record.category);
  (record.tags || []).forEach((tag) => {
    if (tag && !tags.includes(tag)) tags.push(tag);
  });
  return tags;
}

function toSavedRecord(item, existing) {
  return {
    id: collectionItemKey(item),
    title: displayTitle(item),
    url: item.url || existing?.url || "",
    source: item.source || existing?.source || "",
    channel: item.channel || existing?.channel || channelId || "",
    category: item.category || existing?.category || "",
    tags: [...new Set((item.tags || existing?.tags || []).filter(Boolean))],
    author_line: item.author_line || existing?.author_line || "",
    published: String(item.published_at || item.published || existing?.published || "").slice(0, 10),
    summary_zh: item.summary_zh || existing?.summary_zh || "",
    saved_at: existing?.saved_at || new Date().toISOString(),
    note: existing?.note || "",
    note_updated_at: existing?.note_updated_at || "",
  };
}

function toggleSaved(item) {
  const key = collectionItemKey(item);
  if (!key) return false;
  const collection = readCollection();
  if (collection.items[key]) {
    const current = collection.items[key];
    const noteText = (current.note || collection.notes[key]?.note || "").trim();
    if (noteText && !window.confirm("这篇有笔记。取消收藏后笔记仍保留在本机，再次收藏时会恢复。确定取消？")) {
      return true;
    }
    if (current.note) {
      collection.notes[key] = { note: current.note, note_updated_at: current.note_updated_at || "" };
    }
    delete collection.items[key];
    writeCollection(collection);
    return false;
  }
  const kept = collection.notes[key];
  collection.items[key] = toSavedRecord(item, kept ? { ...item, note: kept.note, note_updated_at: kept.note_updated_at } : null);
  writeCollection(collection);
  return true;
}

function saveNote(id, note) {
  const collection = readCollection();
  const current = collection.items[id];
  if (!current) return false;
  current.note = note;
  current.note_updated_at = new Date().toISOString();
  collection.notes[id] = { note: current.note, note_updated_at: current.note_updated_at };
  return writeCollection(collection);
}

function collectionRecords() {
  return Object.values(readCollection().items).sort((left, right) => String(right.saved_at || "").localeCompare(String(left.saved_at || "")));
}

function tagCounts(records) {
  const counts = new Map();
  records.forEach((record) => {
    const tags = recordTags(record);
    if (!tags.length) {
      counts.set(UNTAGGED_LABEL, (counts.get(UNTAGGED_LABEL) || 0) + 1);
      return;
    }
    tags.forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1));
  });
  return [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "zh-CN"));
}

function updateLibraryBadge() {
  const count = Object.keys(readCollection().items).length;
  document.querySelectorAll("[data-library-count]").forEach((node) => {
    node.hidden = count === 0;
    node.textContent = String(count);
  });
}

function setSaveButton(button, saved) {
  if (!button) return;
  button.classList.toggle("is-saved", saved);
  button.setAttribute("aria-pressed", String(saved));
  button.textContent = saved ? "已收藏" : "收藏";
}

function scheduleNoteSave(id, note, status) {
  window.clearTimeout(state.noteTimers[id]);
  if (status) status.textContent = "正在保存…";
  state.noteTimers[id] = window.setTimeout(() => {
    const saved = saveNote(id, note);
    if (status) status.textContent = saved === false ? "本机存储已满，笔记未写入" : "已保存在本机";
    if (page === "library") renderLibraryHero();
  }, 280);
}

function exportCollection() {
  const payload = readCollection();
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  const stamp = dateKey(new Date());
  link.href = URL.createObjectURL(blob);
  link.download = `aix-daily-collection-${stamp}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function mergeImportedCollection(payload) {
  const incoming = payload?.items && !Array.isArray(payload.items) ? payload.items : {};
  const collection = readCollection();
  Object.values(incoming).forEach((item) => {
    const key = collectionItemKey(item);
    if (!key) return;
    const previous = collection.items[key];
    if (!previous) {
      collection.items[key] = toSavedRecord(item, item);
      return;
    }
    const keepIncomingNote = String(item.note_updated_at || "") >= String(previous.note_updated_at || "");
    collection.items[key] = {
      ...toSavedRecord(item, previous),
      saved_at: previous.saved_at || item.saved_at,
      note: keepIncomingNote ? String(item.note || "") : previous.note,
      note_updated_at: keepIncomingNote ? (item.note_updated_at || previous.note_updated_at) : previous.note_updated_at,
    };
  });
  writeCollection(collection);
}

function renderHeatmap() {
  const container = document.getElementById("activity-heatmap");
  if (!container) return;
  const viewing = currentDate();
  const signature = `${state.activity.length}:${[...state.archiveDates].join(",")}:${viewing}:${page}`;
  if (signature === state.heatmapSignature && container.childElementCount) return;
  state.heatmapSignature = signature;
  const fragment = document.createDocumentFragment();
  const relevant = state.activity.filter((item) => page === "home" || item.channel === channelId);
  const byDate = new Map();
  relevant.forEach((item) => {
    const existing = byDate.get(item.date) || { date: item.date, fetched: 0, candidates: 0, selected: 0 };
    existing.fetched += Number(item.fetched) || 0;
    existing.candidates += Number(item.candidates) || 0;
    existing.selected += Number(item.selected) || 0;
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

  ["日", "一", "二", "三", "四", "五", "六"].forEach((label) => {
    const dow = document.createElement("span");
    dow.className = "heatmap__dow";
    dow.textContent = label;
    fragment.appendChild(dow);
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
      fragment.appendChild(month);
    }
    const hasArchive = page === "home" ? state.archiveDates.has(key) : Boolean(item);
    const clickable = hasArchive && value > 0;
    const cell = document.createElement(clickable ? "button" : "span");
    cell.className = "heatmap__day";
    cell.dataset.level = activityLevel(value, maximum);
    cell.dataset.date = key;
    cell.setAttribute("role", "gridcell");
    const label = `${formatDate(key)}：精选 ${value}`;
    cell.title = label;
    cell.setAttribute("aria-label", label);
    if (key === viewing) cell.classList.add("is-current");
    if (clickable) cell.type = "button";
    fragment.appendChild(cell);
    if (value > 0) populatedDays += 1;
    total += value;
  }
  container.replaceChildren(fragment);
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

    const picture = document.createElement("picture");
    const webp = document.createElement("source");
    webp.type = "image/webp";
    webp.srcset = path(`assets/art/${channel.id}.webp`);
    const art = document.createElement("img");
    art.className = "channel-card__art";
    art.src = path(`assets/art/${channel.id}.jpg`);
    art.alt = "";
    art.loading = "lazy";
    art.decoding = "async";
    art.width = 640;
    art.height = 360;
    picture.append(webp, art);

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
    card.append(picture, body);
    container.appendChild(card);
  });
}

function paperSearchText(item) {
  const cached = state.searchIndex.get(item);
  if (cached) return cached;
  const text = [
    displayTitle(item),
    item.summary_zh,
    item.why_it_matters_zh,
    item.abstract_or_text,
    item.abstract,
    item.author_line,
    ...(item.creators || []),
    item.source,
    item.category,
    ...(item.tags || []),
  ].join(" ").toLocaleLowerCase("zh-CN");
  state.searchIndex.set(item, text);
  return text;
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
  const card = fragment.querySelector(".paper-card");
  const key = collectionItemKey(item);
  if (card && key) card.dataset.id = key;
  const saved = savedRecord(item);
  setSaveButton(fragment.querySelector(".save-button"), Boolean(saved));
  const noteBlock = fragment.querySelector(".note-block");
  const noteField = fragment.querySelector(".note-field");
  if (noteBlock) {
    noteBlock.hidden = page !== "library" && !saved;
    if (noteField) noteField.value = saved?.note || "";
  }
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
  const abstract = fragment.querySelector(".abstract-text");
  const details = fragment.querySelector(".abstract-details");
  if (details && abstract) {
    const abstractText = item.abstract_or_text || item.abstract || "该来源未提供摘要或正文。";
    details.addEventListener("toggle", () => {
      if (details.open) abstract.textContent = abstractText;
    }, { once: true });
  }
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

function ensureEmptyArt() {
  const image = document.getElementById("empty-art");
  if (!image || image.getAttribute("src")) return;
  image.src = path("assets/art/empty.jpg");
  const webp = document.getElementById("empty-art-webp");
  if (webp) webp.srcset = path("assets/art/empty.webp");
}

function renderEmptyState(filteredCount) {
  const empty = document.getElementById("empty-state");
  const toolbar = document.querySelector(".toolbar");
  const allCount = payloadItems().length;
  empty.hidden = filteredCount > 0;
  if (filteredCount === 0) ensureEmptyArt();
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
  const total = payloadItems().length;
  setText("result-count", total ? `显示 ${items.length} / ${total} 项` : "");
  renderEmptyState(items.length);
  const fragment = document.createDocumentFragment();
  const groups = new Map();
  items.forEach((item) => {
    const group = page === "home"
      ? (item.channel_name || channelNames[item.channel] || "其他更新")
      : (item.category || "当日收录");
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
    fragment.appendChild(section);
  });
  container.replaceChildren(fragment);
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
    ? `${SITE_NAME} · ${date}`
    : `${channelNames[channelId] || SITE_NAME} · ${date}`;
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

  const artStem = isHome ? "hero" : channelId;
  const art = document.getElementById("hero-art");
  const artWebp = document.getElementById("hero-art-webp");
  if (art) art.src = path(`assets/art/${artStem}.jpg`);
  if (artWebp) artWebp.srcset = path(`assets/art/${artStem}.webp`);

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
  const [manifest, activity] = await Promise.all([
    loadJSON("api/v1/manifest.json"),
    loadJSON("api/v1/activity.json"),
  ]);
  state.manifest = manifest;
  state.activity = activity.items || [];
  renderChannels();
  renderHeatmap();
  markChannelNav();
}

async function loadArchive() {
  const container = document.getElementById("history-list");
  if (!container) return;
  const archivePath = page === "channel"
    ? `data/channels/${channelId}/archive/index.json`
    : "data/daily/archive/index.json";
  try {
    const value = await loadJSON(archivePath);
    const items = value.items || [];
    state.archiveDates = new Set(items.map((item) => item.date).filter(Boolean));
    const viewing = currentDate();
    const fragment = document.createDocumentFragment();
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
      fragment.appendChild(link);
    });
    container.replaceChildren(fragment);
    renderHeatmap();
  } catch (error) {
    container.textContent = `历史列表读取失败：${error.message}`;
  }
}

function flattenHomeItems(payload) {
  let rank = 0;
  payload.items = (payload.channels || []).flatMap((channel) => (
    (channel.items || channel.papers || []).map((item) => {
      rank += 1;
      return {
        ...item,
        rank,
        channel: item.channel || channel.id,
        channel_name: channel.name,
      };
    })
  ));
  return payload;
}

async function loadHomeDigest(date) {
  const url = date ? `data/daily/archive/${encodeURIComponent(date)}.json` : "data/daily/latest.json";
  try {
    return flattenHomeItems(await loadJSON(url));
  } catch (error) {
    throw new Error(date ? `没有 ${date} 的综合日报` : error.message);
  }
}

async function loadDigest() {
  const date = requestedDate();
  const payload = page === "home"
    ? await loadHomeDigest(date)
    : await loadJSON(date
      ? `data/channels/${channelId}/archive/${encodeURIComponent(date)}.json`
      : `data/channels/${channelId}/latest.json`);
  renderPayload(payload);
}

function findRenderableItem(id) {
  return payloadItems().find((item) => collectionItemKey(item) === id) || readCollection().items[id] || null;
}

function bindCollectionEvents(rootId) {
  const rootNode = document.getElementById(rootId);
  if (!rootNode) return;
  rootNode.addEventListener("click", (event) => {
    const button = event.target.closest(".save-button");
    if (!button) return;
    const card = button.closest(".paper-card");
    const item = findRenderableItem(card?.dataset.id);
    if (!item) return;
    const saved = toggleSaved(item);
    setSaveButton(button, saved);
    const noteBlock = card.querySelector(".note-block");
    if (noteBlock && page !== "library") noteBlock.hidden = !saved;
    if (page === "library") renderLibrary();
  });
  rootNode.addEventListener("input", (event) => {
    const field = event.target.closest(".note-field");
    if (!field) return;
    const card = field.closest(".paper-card");
    if (!card?.dataset.id || !savedRecord({ id: card.dataset.id })) return;
    scheduleNoteSave(card.dataset.id, field.value, card.querySelector(".note-status"));
  });
}

function visibleLibraryRecords() {
  const query = state.libraryQuery.trim().toLocaleLowerCase("zh-CN");
  return collectionRecords().filter((record) => {
    const tags = recordTags(record);
    const tagMatch = state.libraryTag === "all"
      || (state.libraryTag === UNTAGGED_LABEL ? tags.length === 0 : tags.includes(state.libraryTag));
    if (!tagMatch) return false;
    if (!query) return true;
    const haystack = [record.title, record.note, record.source, record.author_line, record.category, ...(record.tags || [])]
      .join(" ")
      .toLocaleLowerCase("zh-CN");
    return haystack.includes(query);
  });
}

function renderLibraryHero() {
  const records = collectionRecords();
  setText("library-total", String(records.length));
  setText("library-note-count", String(records.filter((record) => (record.note || "").trim()).length));
}

function renderTagRail(records) {
  const container = document.getElementById("tag-rail");
  if (!container) return;
  const fragment = document.createDocumentFragment();
  const options = [["all", records.length], ...tagCounts(records)];
  options.forEach(([tag, count]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tag-rail__item${state.libraryTag === tag ? " is-active" : ""}`;
    button.dataset.tag = tag;
    button.append(document.createTextNode(tag === "all" ? "全部" : tag));
    const badge = document.createElement("span");
    badge.textContent = String(count);
    button.appendChild(badge);
    fragment.appendChild(button);
  });
  container.replaceChildren(fragment);
}

function renderLibrary() {
  const records = collectionRecords();
  const visible = visibleLibraryRecords();
  renderLibraryHero();
  renderTagRail(records);
  updateLibraryBadge();
  const title = document.getElementById("library-title");
  if (title) title.textContent = state.libraryTag === "all" ? "全部收藏" : state.libraryTag;
  setText("library-result-count", records.length ? `显示 ${visible.length} / ${records.length} 篇` : "");
  const empty = document.getElementById("library-empty");
  const groups = document.getElementById("library-groups");
  if (empty) {
    empty.hidden = visible.length > 0;
    if (visible.length === 0) {
      ensureEmptyArt();
      setText("empty-title", records.length ? "没有匹配的收藏" : "还没有收藏");
      setText("empty-text", records.length
        ? "请更换标签或搜索词。"
        : "在日报条目右上角点「收藏」，条目会按原有标签自动归入这里。笔记只保存在本机。");
    }
  }
  if (!groups) return;
  if (!visible.length) {
    groups.replaceChildren();
    return;
  }
  const grouped = new Map();
  if (state.libraryTag === "all") {
    grouped.set("全部收藏", visible);
  } else {
    grouped.set(state.libraryTag, visible);
  }
  const fragment = document.createDocumentFragment();
  grouped.forEach((values, name) => {
    const section = document.createElement("section");
    section.className = "paper-group";
    const heading = document.createElement("h3");
    heading.className = "group-title";
    heading.append(document.createTextNode(name));
    const count = document.createElement("span");
    count.textContent = `${values.length} 篇`;
    heading.appendChild(count);
    section.appendChild(heading);
    values.forEach((record, index) => {
      section.appendChild(createItemCard({ ...record, rank: index + 1 }, name));
    });
    fragment.appendChild(section);
  });
  groups.replaceChildren(fragment);
}

function bindLibraryPage() {
  let searchTimer = 0;
  document.getElementById("library-search")?.addEventListener("input", (event) => {
    state.libraryQuery = event.target.value;
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(renderLibrary, 120);
  });
  document.getElementById("tag-rail")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tag]");
    if (!button) return;
    state.libraryTag = button.dataset.tag;
    renderLibrary();
  });
  document.getElementById("export-collection")?.addEventListener("click", exportCollection);
  document.getElementById("import-collection")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    const status = document.getElementById("library-status");
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      mergeImportedCollection(payload);
      renderLibrary();
      if (status) {
        status.hidden = false;
        status.textContent = "备份已合并到本机收藏。";
      }
    } catch {
      if (status) {
        status.hidden = false;
        status.textContent = "导入失败：请选择由本站导出的 JSON 备份。";
      }
    }
    event.target.value = "";
  });
  bindCollectionEvents("library-groups");
}

function bindEvents() {
  let searchTimer = 0;
  document.getElementById("search-input")?.addEventListener("input", (event) => {
    state.query = event.target.value;
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(renderItems, 120);
  });
  document.getElementById("source-filters")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-source]");
    if (!button) return;
    state.source = button.dataset.source;
    document.querySelectorAll("button[data-source]").forEach((item) => item.classList.toggle("is-active", item === button));
    renderItems();
  });
  document.getElementById("activity-heatmap")?.addEventListener("click", (event) => {
    const cell = event.target.closest("button.heatmap__day[data-date]");
    if (!cell) return;
    location.href = `?date=${encodeURIComponent(cell.dataset.date)}`;
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
  bindCollectionEvents("paper-groups");
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
updateLibraryBadge();
if (page === "library") {
  bindLibraryPage();
  renderLibrary();
} else {
  bindEvents();
  loadDigest().catch(showLoadError);
  loadManifestAndActivity().catch((error) => {
    const summary = document.getElementById("activity-summary");
    if (summary) summary.textContent = `活动数据读取失败：${error.message}`;
  });
  loadArchive();
}
