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

const state = { charts: [], showEvents: true, events: [] };

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function theme() {
  return {
    ink: css('--ink'),
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

function traces(series) {
  const dense = series.lines.some((line) => line.points.length > MARKER_THRESHOLD);
  const format = (series.y || {}).tickformat;
  return series.lines.map((line, i) => ({
    type: 'scatter',
    mode: dense ? 'lines' : 'lines+markers',
    name: line.name,
    x: line.points.map((p) => p[0]),
    y: line.points.map((p) => p[1]),
    line: { color: colourFor(line.name, i), width: 2, shape: series.line_shape || 'linear' },
    marker: { size: 5 },
    connectgaps: false,
    /* Match the axis formatting, or the tooltip shows raw 35802000000. */
    yhoverformat: format,
    hovertemplate: '%{y}<extra>%{fullData.name}</extra>',
  }));
}

/* Event markers are clipped to the data's own date range -- a release that
 * predates the series would otherwise stretch the axis to fit it. */
function eventDecorations(series, palette) {
  if (!state.showEvents || !series.annotations) return { shapes: [], annotations: [] };

  const dates = series.lines.flatMap((line) => line.points.map((p) => p[0]));
  if (!dates.length) return { shapes: [], annotations: [] };
  const first = dates.reduce((a, b) => (a < b ? a : b));
  const last = dates.reduce((a, b) => (a > b ? a : b));

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
  const decorations = eventDecorations(series, palette);

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
      gridcolor: palette.rule,
      zeroline: false,
      linecolor: palette.rule,
    },
    yaxis: {
      type: logScale ? 'log' : 'linear',
      title: { text: y.title || '', font: { size: 12 } },
      tickformat: y.tickformat,
      /* One label per decade; Plotly's default log ticks label every minor
       * gridline and the axis turns into a wall of numbers. */
      dtick: logScale ? 1 : undefined,
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

  const source = el('span');
  source.append('Source: ');
  const link = el('a', null, meta.source.name);
  link.href = meta.source.url;
  link.rel = 'noopener';
  source.append(link);
  if (meta.source.license) source.append(` (${meta.source.license})`);
  row.append(source);

  const updated = (series && series.updated) || meta.updated;
  if (updated) row.append(el('span', null, `Updated ${updated.slice(0, 10)}`));
  if (meta.mode === 'append') row.append(el('span', null, 'Recorded daily; no history before collection began'));
  if (!meta.ok) {
    row.append(el('span', 'badge', series ? 'Last refresh failed — showing previous data' : 'Refresh failed'));
  }
  return row;
}

function buildCard(meta, series) {
  const card = el('section', 'card');
  card.id = meta.id;

  const head = el('div', 'card-head');
  head.append(el('h3', null, meta.title));

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
}

main().catch((error) => {
  document.getElementById('charts').innerHTML =
    `<p class="empty">Could not load chart data: ${error}</p>`;
});
