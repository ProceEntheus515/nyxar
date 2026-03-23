import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as d3 from 'd3';
import { useStore } from '../store';
import { scoreToSeverity, RISK_COLORS } from '../lib/utils';
import { readCssVar } from '../styles/cssVar';
import Card from '../components/ui/Card';
import RiskBadge from '../components/ui/RiskBadge';
import MonoText from '../components/ui/MonoText';
import MetricCard from '../components/data/MetricCard';

export default function NetworkMap() {
  const svgRef = useRef(null);
  const measureRef = useRef(null);
  const { identities, events, alerts, openDetailPanel } = useStore();
  const [selectedNode, setSelectedNode] = useState(null);
  const [chartSize, setChartSize] = useState({ width: 0, height: 0 });

  // Computar Grafo Unificado (Identidades Locales + Nube/Destinos Activos últimos 5m)
  const graphData = useMemo(() => {
    const nodesMap = new Map();
    const linksMap = new Map();
    const now = Date.now();
    const fallbackMuted = readCssVar('--base-subtle') || 'var(--base-subtle)';
    const externalFill = readCssVar('--base-border-strong') || 'var(--base-border-strong)';
    const nodeStroke = readCssVar('--base-deep') || 'var(--base-deep)';

    // Nodos Base (Identidades de la empresa)
    Object.values(identities || {}).forEach(id => {
      nodesMap.set(id.id || id.ip_asociada, {
        id: id.id || id.ip_asociada,
        type: 'identity',
        data: id,
        radius: Math.max(15, (id.risk_score || 0) / 2 + 10),
        color: RISK_COLORS[scoreToSeverity(id.risk_score || 0)]?.bg || fallbackMuted,
      });
    });

    // Validar eventos de últimos 5 minutos
    (events || []).slice(0, 300).forEach(ev => {
      const evtTs = new Date(ev.timestamp).getTime();
      if (now - evtTs > 5 * 60 * 1000) return; // Fuera ventana 5 min
      if (!ev.interno || !ev.externo) return;

      const srcId = ev.interno.id_usuario || ev.interno.ip;
      const dstId = ev.externo.valor;

      // Generar Nodo Destino si no existe (External internet / IPs)
      if (!nodesMap.has(dstId)) {
        nodesMap.set(dstId, {
          id: dstId,
          type: 'external',
          data: { label: dstId },
          radius: 8,
          color: externalFill,
        });
      }

      // Link aggregation weight
      const linkId = `${srcId}-${dstId}`;
      const isIncident = alerts?.some(al => al.host_afectado === srcId && JSON.stringify(al).includes(dstId));
      
      if (!linksMap.has(linkId)) {
        linksMap.set(linkId, {
          source: srcId,
          target: dstId,
          value: 1,
          isIncident: isIncident,
          color: isIncident ? 'var(--color-critical)' : 'var(--color-primary)'
        });
      } else {
        const link = linksMap.get(linkId);
        link.value += 1;
        if (isIncident) {
             link.isIncident = true;
             link.color = 'var(--color-critical)';
        }
      }
    });

    // Solo conservar nodos que tienen conexión o son identidades puras
    const validLinks = Array.from(linksMap.values()).filter(l => nodesMap.has(l.source) && nodesMap.has(l.target));
    
    return {
      nodes: Array.from(nodesMap.values()),
      links: validLinks,
      nodeStroke,
    };
  }, [identities, events, alerts]);

  const recentEvents5m = useMemo(() => {
    const now = Date.now();
    return (events || []).filter(
      (ev) => now - new Date(ev.timestamp).getTime() <= 5 * 60 * 1000,
    ).length;
  }, [events]);

  useEffect(() => {
    const el = measureRef.current;
    if (!el) return undefined;
    const measure = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      setChartSize((prev) => (prev.width === w && prev.height === h ? prev : { width: w, height: h }));
    };
    measure();
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(measure);
      ro.observe(el);
      return () => ro.disconnect();
    }
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  useEffect(() => {
    const width = chartSize.width;
    const height = chartSize.height;
    if (!svgRef.current || width < 48 || height < 48) return;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    svg.selectAll('*').remove();

    const g = svg.append('g');

    svg.call(d3.zoom().on('zoom', (event) => {
      g.attr('transform', event.transform);
    }));

    const nodes = graphData.nodes.map(d => ({ ...d }));
    const links = graphData.links.map(d => ({ ...d }));
    const strokeColor = graphData.nodeStroke || readCssVar('--base-deep');

    const cx = width / 2;
    const cy = height / 2;
    const n = nodes.length;
    nodes.forEach((d, i) => {
      const angle = (i / Math.max(n, 1)) * Math.PI * 2;
      const spread = Math.min(width, height) * 0.12;
      d.x = cx + Math.cos(angle) * spread;
      d.y = cy + Math.sin(angle) * spread;
    });

    const linkCount = Math.max(links.length, 1);
    const chargeMag = n <= 10 ? Math.min(160, 60 + n * 12) : Math.min(320, 100 + n * 18);
    const linkDist = Math.max(48, Math.min(100, (width + height) / (4 + linkCount * 0.15)));

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(linkDist).strength(0.7))
      .force('charge', d3.forceManyBody().strength(-chargeMag))
      .force('center', d3.forceCenter(cx, cy))
      .force('collide', d3.forceCollide().radius(d => d.radius + 6).strength(0.9))
      .force('x', d3.forceX(cx).strength(n <= 12 ? 0.06 : 0.02))
      .force('y', d3.forceY(cy).strength(n <= 12 ? 0.06 : 0.02));

    // Glow filter
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Aristas
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => d.color)
      .attr('stroke-width', d => Math.min(Math.max(1, d.value / 2), 5))
      .attr('stroke-opacity', 0.6)
      .attr('filter', d => d.isIncident ? 'url(#glow)' : null);

    // Nodos
    const nodeGroup = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x; d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      )
      .on('click', (event, d) => {
        if (d.type === 'identity') setSelectedNode(d.data);
      });

    // Círculos
    nodeGroup.append('circle')
      .attr('r', d => d.radius)
      .attr('fill', d => d.color)
      .attr('stroke', strokeColor)
      .attr('stroke-width', 2)
      .style('cursor', 'pointer');

    // Labels para identidades
    nodeGroup.append('text')
      .filter(d => d.type === 'identity')
      .text(d => d.data.nombre_completo?.split(' ')[0] || d.id)
      .attr('x', 0)
      .attr('y', d => d.radius + 15)
      .attr('text-anchor', 'middle')
      .style('fill', 'var(--text-main)')
      .style('font-size', '11px')
      .style('font-family', 'var(--font-ui, sans-serif)')
      .style('pointer-events', 'none');

    const pad = 12;
    simulation.on('tick', () => {
      nodes.forEach((d) => {
        const r = (d.radius || 8) + pad;
        d.x = Math.max(r, Math.min(width - r, d.x));
        d.y = Math.max(r, Math.min(height - r, d.y));
      });

      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      nodeGroup.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [graphData, chartSize.width, chartSize.height]);

  // Encontrar eventos locales al panel
  const nodeEvents = useMemo(() => {
    if (!selectedNode) return [];
    return (events || [])
      .filter(e => e.interno?.id_usuario === selectedNode.id || e.interno?.ip === selectedNode.ip_asociada)
      .slice(0, 5);
  }, [events, selectedNode]);

  return (
    <div className="relative flex min-h-0 w-full min-w-0 flex-1 flex-col">
      <h2 className="mb-3 shrink-0 text-xl font-semibold text-[var(--base-bright)]">
        Internal Topology & Connections
      </h2>

      <div className="mb-3 grid shrink-0 grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCard label="Nodos en grafo" value={graphData.nodes.length} />
        <MetricCard label="Aristas activas" value={graphData.links.length} />
        <MetricCard label="Eventos (5 min)" value={recentEvents5m} />
      </div>

      <div
        ref={measureRef}
        className="relative min-h-[min(60vh,520px)] w-full flex-1 overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--base-deep)]"
      >
        <svg ref={svgRef} className="absolute inset-0 block h-full w-full" />
      </div>

      {selectedNode && (
        <Card className="absolute top-4 right-4 w-[360px] p-0 z-20 flex flex-col shadow-2xl animate-slide-in-right bg-[var(--base-surface)]/95 backdrop-blur">
           <div className="p-4 border-b border-[var(--base-border)] flex justify-between items-start">
             <div>
               <h3 className="font-bold text-white text-[15px]">{selectedNode.nombre_completo}</h3>
               <p className="text-[11px] text-[var(--color-primary)] uppercase tracking-wider mt-1">{selectedNode.area}</p>
             </div>
             <button onClick={() => setSelectedNode(null)} className="text-[var(--text-sec)] hover:text-white">✕</button>
           </div>
           
           <div className="p-4 flex-1">
             <div className="flex gap-4 mb-4">
               <div>
                 <p className="text-[11px] text-[var(--text-sec)]">Riesgo Actual</p>
                 <RiskBadge score={selectedNode.risk_score || 0} severidad={scoreToSeverity(selectedNode.risk_score || 0)} />
               </div>
               <div>
                  <p className="text-[11px] text-[var(--text-sec)]">IP Address</p>
                  <MonoText>{selectedNode.ip_asociada || 'N/A'}</MonoText>
               </div>
             </div>

             <div className="mt-4">
               <h4 className="text-[11px] uppercase tracking-wider text-[var(--text-sec)] mb-2">Últimos Conectados</h4>
               <div className="space-y-2">
                 {nodeEvents.length === 0 ? (
                   <div className="text-xs text-[var(--text-sec)] text-center p-4">Sin actividad reciente</div>
                 ) : (
                   nodeEvents.map(ev => (
                     <div key={ev.id} className="bg-[var(--base-deep)] p-2 rounded border border-[var(--base-border)] text-xs flex justify-between items-center group">
                        <MonoText className="truncate w-2/3">{ev.externo?.valor || ev.source}</MonoText>
                        <span className="text-[10px] text-[var(--text-sec)] shrink-0">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                     </div>
                   ))
                 )}
               </div>
             </div>
             
             <button
               type="button"
               className="w-full mt-4 py-2 border border-[var(--base-border)] text-white rounded text-sm hover:bg-[var(--border-default)] transition-colors"
               onClick={() => {
                 const id = selectedNode?.id ?? selectedNode?.ip_asociada
                 if (id != null) openDetailPanel('identity', id)
               }}
             >
               Abrir en panel de detalle
             </button>
           </div>
        </Card>
      )}
    </div>
  );
}

