import React, { useState, useMemo, useCallback } from 'react';
import { List, useListRef } from 'react-window';
import Card from '../components/ui/Card';
import TimeAgo from '../components/ui/TimeAgo';
import RiskBadge from '../components/ui/RiskBadge';
import AreaBadge from '../components/ui/AreaBadge';
import MonoText from '../components/ui/MonoText';
import { useStore } from '../store';

// SVGs Profesionales para Fuentes
const SourceIcon = ({ source }) => {
  const s = (source || '').toLowerCase();
  if (s.includes('dns')) {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </svg>
    );
  }
  if (s.includes('proxy') || s.includes('squid')) {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-info)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
        <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
        <line x1="6" y1="6" x2="6.01" y2="6"></line>
        <line x1="6" y1="18" x2="6.01" y2="18"></line>
      </svg>
    );
  }
  if (s.includes('firewall')) {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-critical)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="3" y1="9" x2="21" y2="9"></line>
        <line x1="3" y1="15" x2="21" y2="15"></line>
        <line x1="9" y1="9" x2="9" y2="21"></line>
        <line x1="15" y1="3" x2="15" y2="15"></line>
      </svg>
    );
  }
  if (s.includes('wazuh') || s.includes('endpoint')) {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
        <polyline points="2 17 12 22 22 17"></polyline>
        <polyline points="2 12 12 17 22 12"></polyline>
      </svg>
    );
  }
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-sec)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="12 16 16 12 12 8"></polyline>
      <line x1="8" y1="12" x2="16" y2="12"></line>
    </svg>
  );
};

function timelineRowHeight(index, { filteredEvents, alerts }) {
  const e = filteredEvents[index];
  if (!e) return 120;
  const isIncident = alerts.some((al) => al.evento_original_id === e.id);
  return isIncident ? 160 : 120;
}

function TimelineRow({ index, style, ariaAttributes, filteredEvents, alerts }) {
  const e = filteredEvents[index];
  if (!e) return null;

  const isIncident = alerts.some((al) => al.evento_original_id === e.id);
  const incidentData = alerts.find((al) => al.evento_original_id === e.id);
  const hasRisk = (e.enrichment?.risk_score || 0) > 40;

  return (
    <div style={{ ...style, paddingBottom: '8px' }} {...ariaAttributes}>
      <Card
        className={`h-full flex flex-col p-4 animate-fade-in ${isIncident ? 'border-l-4' : ''}`}
        style={isIncident ? { borderLeftColor: 'var(--color-critical)' } : {}}
        glow={isIncident}
        glowColor={incidentData?.severidad === 'CRÍTICA' ? 'var(--color-critical)' : 'transparent'}
      >
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-3">
            <SourceIcon source={e.source} />
            <TimeAgo timestamp={e.timestamp} />
          </div>
          {hasRisk && !isIncident && <RiskBadge score={e.enrichment.risk_score} severidad="alta" />}
          {isIncident && <RiskBadge score={null} severidad={incidentData.severidad} />}
        </div>

        <div className="flex items-center gap-3 mb-2">
          <AreaBadge area={e.interno?.area || 'Desconocido'} />
          <MonoText className="truncate w-1/2">{e.interno?.id_usuario || e.interno?.ip}</MonoText>
        </div>

        <p className="text-sm text-[var(--text-main)] truncate mt-1">
          Revisión hacia <MonoText>{e.externo?.valor}</MonoText>
        </p>

        {isIncident && (
          <div className="mt-2 text-xs text-[var(--color-critical)] rounded bg-[#FF4757]/10 p-2 border border-[var(--color-critical)]">
            {incidentData.descripcion}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function Timeline() {
  const { events, alerts } = useStore();
  const [filterSource, setFilterSource] = useState('');
  const [isScrolled, setIsScrolled] = useState(false);
  const listRef = useListRef();

  const filteredEvents = useMemo(() => {
    let evts = events || [];
    if (filterSource) {
      evts = evts.filter((e) => e.source?.toLowerCase().includes(filterSource));
    }
    return evts;
  }, [events, filterSource]);

  const rowProps = useMemo(() => ({ filteredEvents, alerts }), [filteredEvents, alerts]);

  const handleRowsRendered = useCallback((visible) => {
    setIsScrolled(visible.startIndex > 0);
  }, []);

  const scrollToTop = () => {
    listRef.current?.scrollToRow({ index: 0, behavior: 'instant' });
    setIsScrolled(false);
  };

  return (
    <div className="h-full flex flex-col relative w-full h-[calc(100vh-100px)]">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h2 className="text-xl font-semibold text-white">Live Event Timeline</h2>
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          className="bg-[var(--bg-card)] border border-[var(--border-default)] rounded p-2 text-sm text-white outline-none"
        >
          <option value="">Todas las Fuentes</option>
          <option value="dns">DNS</option>
          <option value="proxy">Proxy</option>
          <option value="firewall">Firewall</option>
          <option value="wazuh">Wazuh</option>
        </select>
      </div>

      {isScrolled && (
        <button
          type="button"
          onClick={scrollToTop}
          className="absolute top-16 left-1/2 -translate-x-1/2 z-10 bg-[var(--color-primary)] text-black px-4 py-1.5 rounded-full font-bold text-xs shadow-lg shadow-[var(--color-primary)]/20 animate-slide-in-right"
        >
          Volver arriba
        </button>
      )}

      <div className="flex-1 w-full relative">
        <List
          listRef={listRef}
          rowCount={filteredEvents.length}
          rowHeight={timelineRowHeight}
          rowComponent={TimelineRow}
          rowProps={rowProps}
          onRowsRendered={handleRowsRendered}
          style={{ height: 800, width: '100%' }}
        />
      </div>
    </div>
  );
}
