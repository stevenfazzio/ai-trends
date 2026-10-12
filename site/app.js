/* Renders one Plotly chart per series listed in data/manifest.json.
 *
 * Everything on the page is driven by the manifest, so adding a chart is a
 * change to the Python registry alone -- no edits here. */

const PALETTE = [
  '#2f6fdd', '#e2622a', '#189f6d', '#a259d9',
  '#d4a017', '#c94f7c', '#4aa3c7', '#7a8794',
];

/* Regions keep the same colour wherever they appear. */
const NAMED_COLOURS = {
  'United States': '#2f6fdd',
  'China': '#e2622a',
  'Rest of world': '#7a8794',
};

/* Charts with few points get visible markers; dense ones would be a smear. */
const MARKER_THRESHOLD = 60;

const state = { charts: [], showEvents: false, events: [] };

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function theme() {
  return {
    ink: css('--ink'),
    panel: css('--panel'),
    soft: css('--ink-soft'),
    faint: css('--ink-faint'),
    rule: css('--rule'),
  };
}

function colourFor(name, index) {
  return NAMED_COLOURS[name] || PALETTE[index % PALETTE.length];
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

/* ---- chart construction ------------------------------------------------ */

/* A point with an empty label is the line being carried forward, not an
 * observation, so it gets no marker. */
function pointMarkers(line) {
  if (!line.labels) return { size: 5 };
  /* Given sizes per point, Plotly assumes a bubble chart and fades the markers
   * and rings them in white. */
  return { size: line.labels.map((label) => (label ? 7 : 0)), opacity: 1, line: { width: 0 } };
}

/* Hollow points are drawn as a second layer over the line's own markers,
 * filled with the card's colour so the line does not show through. Styling
 * them on the line itself would hand the legend whatever its first point is. */
function hollowOverlay(line, colour, palette) {
  const at = (line.hollow || []).flatMap((flag, i) => (flag ? [i] : []));
  if (!at.length) return [];
  return [{
    type: 'scatter',
    mode: 'markers',
    x: at.map((i) => line.points[i][0]),
    y: at.map((i) => line.points[i][1]),
    marker: { size: 7, color: palette.panel, line: { color: colour, width: 1.5 } },
    showlegend: false,
    hoverinfo: 'skip',
  }];
}

function traces(series) {
  const dense = series.lines.some((line) => line.points.length > MARKER_THRESHOLD);
  const format = (series.y || {}).tickformat;
  const palette = theme();

  return series.lines.flatMap((line, i) => {
    const colour = colourFor(line.name, i);
    const trace = {
      type: 'scatter',
      mode: dense ? 'lines' : 'lines+markers',
      name: line.name,
      x: line.points.map((p) => p[0]),
      y: line.points.map((p) => p[1]),
      text: line.labels && line.labels.map((label) => (label ? ` \u00b7 ${label}` : '')),
      line: { color: colour, width: 2, shape: series.line_shape || 'linear' },
      marker: pointMarkers(line),
      connectgaps: false,
      /* Match the axis formatting, or the tooltip shows raw 35802000000. */
      yhoverformat: format,
      hovertemplate: `%{y}${line.labels ? '%{text}' : ''}<extra>%{fullData.name}</extra>`,
    };
    return [trace, ...hollowOverlay(line, colour, palette)];
  });
}

/* One label per decade suits a series spanning many of them, and leaves one
 * spanning barely one with a single label. A narrow series gets ticks at 1, 2
 * and 5 instead. Plotly cannot be left to label them: its own 1-2-5 mode
 * writes only the leading digit, so that 20 reads "2", and given the values it
 * drops the axis prefix and suffix. So the labels are written here. */
const NARROW_LOG_DECADES = 1.5;
const TICK_NUMBER = new Intl.NumberFormat('en', { notation: 'compact', maximumSignificantDigits: 3 });

function logTicks(series) {
  const values = series.lines.flatMap((line) => line.points.map((p) => p[1])).filter((v) => v > 0);
  if (!values.length) return { dtick: 1 };
  const low = Math.log10(Math.min(...values));
  const high = Math.log10(Math.max(...values));
  if (high - low >= NARROW_LOG_DECADES) return { dtick: 1 };

  const y = series.y || {};
  const tickvals = [];
  for (let decade = Math.floor(low) - 1; decade <= Math.ceil(high); decade += 1) {
    [1, 2, 5].forEach((digit) => tickvals.push(digit * 10 ** decade));
  }
  const ticktext = tickvals.map(
    (value) => `${y.tickprefix || ''}${TICK_NUMBER.format(value)}${y.ticksuffix || ''}`
  );
  return { tickmode: 'array', tickvals, ticktext };
}

const DAY_MS = 86400000;

/* An append-mode series starts life with a single observation. Left to
 * autorange, Plotly fits the axis to that one instant and labels it down to
 * fractions of a second; this keeps a minimum window either side. */
const MIN_SPAN_DAYS = 14;

function dateExtent(series) {
  const dates = series.lines.flatMap((line) => line.points.map((p) => p[0]));
  if (!dates.length) return null;
  return {
    first: dates.reduce((a, b) => (a < b ? a : b)),
    last: dates.reduce((a, b) => (a > b ? a : b)),
  };
}

function paddedRange(extent) {
  const first = Date.parse(extent.first);
  const last = Date.parse(extent.last);
  const spanDays = (last - first) / DAY_MS;
  if (spanDays >= MIN_SPAN_DAYS) return undefined; // autorange is fine

  const pad = ((MIN_SPAN_DAYS - spanDays) / 2) * DAY_MS;
  const iso = (ms) => new Date(ms).toISOString().slice(0, 10);
  return [iso(first - pad), iso(last + pad)];
}

/* Event markers are clipped to the data's own date range -- a release that
 * predates the series would otherwise stretch the axis to fit it. */
function eventDecorations(series, palette, extent) {
  if (!state.showEvents || !series.annotations || !extent) {
    return { shapes: [], annotations: [] };
  }
  const { first, last } = extent;

  const shapes = [];
  const annotations = [];
  state.events
    .filter((e) => e.date >= first && e.date <= last)
    .forEach((e, i) => {
      shapes.push({
        type: 'line',
        x0: e.date, x1: e.date,
        y0: 0, y1: 1, yref: 'paper',
        line: { color: palette.faint, width: 1, dash: 'dot' },
        layer: 'below',
      });
      /* Vertical labels inside the plot. Horizontal ones collide as soon as
       * two releases land in the same quarter, which is most of them. */
      annotations.push({
        x: e.date,
        y: 0.98,
        yref: 'paper',
        yanchor: 'top',
        xanchor: 'center',
        xshift: -7,
        textangle: -90,
        text: e.label,
        showarrow: false,
        font: { size: 10, color: palette.faint },
      });
    });
  return { shapes, annotations };
}

function layoutFor(series, logScale) {
  const palette = theme();
  const y = series.y || {};
  const extent = dateExtent(series);
  const decorations = eventDecorations(series, palette, extent);

  return {
    margin: { l: 68, r: 18, t: 26, b: 40 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: palette.soft, size: 12 },
    hovermode: 'x unified',
    hoverlabel: { align: 'left' },
    showlegend: series.lines.length > 1,
    legend: { orientation: 'h', y: -0.14, x: 0, font: { size: 12 } },
    xaxis: {
      type: 'date',
      range: extent ? paddedRange(extent) : undefined,
      gridcolor: palette.rule,
      zeroline: false,
      linecolor: palette.rule,
    },
    yaxis: {
      type: logScale ? 'log' : 'linear',
      title: { text: y.title || '', font: { size: 12 } },
      tickformat: y.tickformat,
      tickprefix: y.tickprefix,
      ticksuffix: y.ticksuffix,
      /* Plotly's default log ticks label every minor gridline and the axis
       * turns into a wall of numbers. */
      ...(logScale ? logTicks(series) : {}),
      /* rangemode is meaningless on a log axis and Plotly warns about it. */
      rangemode: !logScale && y.rangemode ? y.rangemode : 'normal',
      gridcolor: palette.rule,
      zeroline: false,
      linecolor: palette.rule,
    },
    ...decorations,
  };
}

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

function renderChart(chart) {
  Plotly.react(chart.node, traces(chart.series), layoutFor(chart.series, chart.log), PLOT_CONFIG);
}

/* ---- card assembly ----------------------------------------------------- */

function provenance(meta, series) {
  const row = el('div', 'provenance');

  const sources = meta.sources || [];
  sources.forEach((source, i) => {
    const span = el('span');
    if (i === 0) span.append(sources.length > 1 ? 'Sources: ' : 'Source: ');
    const link = el('a', null, source.name);
    link.href = source.url;
    link.rel = 'noopener';
    span.append(link);
    if (source.license) span.append(` (${source.license})`);
    row.append(span);
  });

  const updated = (series && series.updated) || meta.updated;
  if (updated) row.append(el('span', null, `Updated ${updated.slice(0, 10)}`));
  if (meta.mode === 'append') row.append(el('span', null, 'Recorded daily; no history before collection began'));
  if (!meta.ok) {
    row.append(el('span', 'badge', series ? 'Last refresh failed — showing previous data' : 'Refresh failed'));
  }
  return row;
}

/* A link to the card itself, as a small icon after its title. Following it
 * puts the anchor in the address bar; it also copies the address, since
 * wanting to paste it somewhere is the usual reason for clicking, and the icon
 * turns to a tick for a moment to say so. */
const ICON = (shape) =>
  `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" ` +
  `stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${shape}</svg>`;
const LINK_ICON = ICON(
  '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>' +
  '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
);
const TICK_ICON = ICON('<path d="M20 6 9 17l-5-5"/>');

function anchorLink(id) {
  const link = el('a', 'anchor');
  link.href = `#${id}`;
  link.title = 'Copy link to this chart';
  link.setAttribute('aria-label', 'Copy link to this chart');
  link.innerHTML = LINK_ICON;
  link.addEventListener('click', () => {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(link.href).then(() => {
      link.innerHTML = TICK_ICON;
      link.classList.add('copied');
      setTimeout(() => {
        link.innerHTML = LINK_ICON;
        link.classList.remove('copied');
      }, 1600);
    }, () => {});
  });
  return link;
}

function buildCard(meta, series) {
  const card = el('section', 'card');
  card.id = meta.id;

  const head = el('div', 'card-head');
  const title = el('h3', null, meta.title);
  /* Tied to the title's last word, so it never wraps onto a line of its own. */
  title.append('\u00a0', anchorLink(meta.id));
  head.append(title);

  const chart = { node: null, series, log: !!(meta.y && meta.y.log) };

  if (series) {
    /* Labelled with what the click does, not with the current state -- a button
     * reading "Log scale" on an already-logarithmic chart is a coin flip. */
    const label = () => (chart.log ? 'Switch to linear' : 'Switch to log');
    const button = el('button', 'scale-btn', label());
    button.addEventListener('click', () => {
      chart.log = !chart.log;
      button.textContent = label();
      renderChart(chart);
    });
    head.append(button);
  }
  card.append(head);

  if (meta.description) card.append(el('p', 'desc', meta.description));

  if (series && series.lines.length) {
    chart.node = el('div', 'plot');
    card.append(chart.node);
    chart.series = { ...meta, ...series };
    state.charts.push(chart);
  } else {
    card.append(el('p', 'empty', 'No data recorded yet.'));
  }

  if (meta.notes) card.append(el('p', 'notes', meta.notes));
  card.append(provenance(meta, series));
  return card;
}

/* ---- page -------------------------------------------------------------- */

async function fetchSeries(id, version) {
  try {
    const response = await fetch(`data/${id}.json?v=${encodeURIComponent(version)}`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

async function main() {
  const manifest = await (await fetch(`data/manifest.json?t=${Date.now()}`)).json();
  state.events = manifest.events || [];
  /* The markers start off, but a browser may restore the box as it was left on
   * a reload, so the box is asked rather than assumed. */
  state.showEvents = document.getElementById('events-toggle').checked;

  const charts = document.getElementById('charts');
  charts.innerHTML = '';
  const nav = document.getElementById('nav');

  for (const group of manifest.groups) {
    const link = el('a', null, group.title);
    link.href = `#group-${group.id}`;
    nav.append(link);

    const section = el('section', 'group');
    section.id = `group-${group.id}`;
    section.append(el('h2', null, group.title));
    if (group.blurb) section.append(el('p', 'blurb', group.blurb));

    const cards = await Promise.all(
      group.series.map(async (meta) => buildCard(meta, await fetchSeries(meta.id, manifest.generated)))
    );
    cards.forEach((card) => section.append(card));
    charts.append(section);
  }

  state.charts.forEach(renderChart);

  document.getElementById('generated').textContent =
    `Page rebuilt ${manifest.generated.replace('T', ' ').replace('Z', ' UTC')}.`;

  const toggle = document.getElementById('events-toggle');
  toggle.addEventListener('change', () => {
    state.showEvents = toggle.checked;
    state.charts.forEach(renderChart);
  });

  /* Re-render on theme flips so axis and grid colours follow the OS. */
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => state.charts.forEach(renderChart));

  /* The browser looks for the address's anchor as the page loads, before any
   * card exists, so a link to a chart has to be followed again now. */
  const target = document.getElementById(location.hash.slice(1));
  if (target) target.scrollIntoView();
}

main().catch((error) => {
  document.getElementById('charts').innerHTML =
    `<p class="empty">Could not load chart data: ${error}</p>`;
});
