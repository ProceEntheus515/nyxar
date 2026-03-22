import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as d3 from 'd3';
import { useStore } from '../store';
import { scoreToSeverity, RISK_COLORS } from '../lib/utils';
import Card from '../components/ui/Card';
import RiskBadge from '../components/ui/RiskBadge';
import MonoText from '../components/ui/MonoText';

export default function NetworkMap() {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const { identities, events, alerts } = useStore();
  const [selectedNode, setSelectedNode] = useState(null);

  // Computar Grafo Unificado (Identidades Locales + Nube/Destinos Activos últimos 5m)
  const graphData = useMemo(() => {
    const nodesMap = new Map();
    const linksMap = new Map();
    const now = Date.now();

    // Nodos Base (Identidades de la empresa)
    Object.values(identities || {}).forEach(id => {
      nodesMap.set(id.id || id.ip_asociada, {
        id: id.id || id.ip_asociada,
        type: 'identity',
        data: id,
        radius: Math.max(15, (id.risk_score || 0) / 2 + 10),
        color: RISK_COLORS[scoreToSeverity(id.risk_score || 0)]?.bg || '#8B949E'
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
          color: '#21262D' // Gris opaco para internet general
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
      links: validLinks
    };
  }, [identities, events, alerts]);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);

    svg.selectAll('*').remove();

    const g = svg.append('g');

    // Pan & Zoom
    svg.call(d3.zoom().on('zoom', (event) => {
      g.attr('transform', event.transform);
    }));

    // Datos copiados para simulación porque D3 muta los objetos
    const nodes = graphData.nodes.map(d => ({...d}));
    const links = graphData.links.map(d => ({...d}));

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(d => d.radius + 5));

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
      .attr('stroke', '#0D1117')
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
      .style('font-family', 'Inter')
      .style('pointer-events', 'none');

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      nodeGroup.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [graphData]);

  // Encontrar eventos locales al panel
  const nodeEvents = useMemo(() => {
    if (!selectedNode) return [];
    return (events || [])
      .filter(e => e.interno?.id_usuario === selectedNode.id || e.interno?.ip === selectedNode.ip_asociada)
      .slice(0, 5);
  }, [events, selectedNode]);

  return (
    <div className="relative w-full h-[calc(100vh-80px)]" ref={containerRef}>
      <h2 className="absolute top-4 left-4 text-xl font-semibold text-white z-10 pointer-events-none">
        Internal Topology & Connections
      </h2>
      
      <svg ref={svgRef} className="w-full h-full bg-[#0D1117] rounded-lg border border-[var(--border-default)]" />

      {selectedNode && (
        <Card className="absolute top-4 right-4 w-[360px] p-0 z-20 flex flex-col shadow-2xl animate-slide-in-right bg-[#161B22]/95 backdrop-blur">
           <div className="p-4 border-b border-[#21262D] flex justify-between items-start">
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
                     <div key={ev.id} className="bg-[#0D1117] p-2 rounded border border-[#21262D] text-xs flex justify-between items-center group">
                        <MonoText className="truncate w-2/3">{ev.externo?.valor || ev.source}</MonoText>
                        <span className="text-[10px] text-[var(--text-sec)] shrink-0">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                     </div>
                   ))
                 )}
               </div>
             </div>
             
             <button className="w-full mt-4 py-2 border border-[#21262D] text-white rounded text-sm hover:bg-[var(--border-default)] transition-colors">
               Abrir Reporte Completo
             </button>
           </div>
        </Card>
      )}
    </div>
  );
}
