import { useMemo, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, ValueFormatterParams, CellClassParams } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { OpenPosition, ClosedPosition } from '../types';
import { formatCurrency, formatPercent, formatDate } from '../utils/api';

interface OpenPositionGridProps {
  positions: OpenPosition[];
  showInTop20Column?: boolean;
  acknowledgedIds: Set<string>;
  onAcknowledge: (id: string) => void;
}

export function OpenPositionGrid({
  positions,
  showInTop20Column = false,
  acknowledgedIds,
  onAcknowledge
}: OpenPositionGridProps) {

  const columnDefs = useMemo<ColDef<OpenPosition>[]>(() => {
    const cols: ColDef<OpenPosition>[] = [
      {
        headerName: '#',
        valueGetter: (params) => params.node?.rowIndex != null ? params.node.rowIndex + 1 : '',
        width: 50,
        pinned: 'left',
      },
      {
        headerName: 'Ticker',
        field: 'ticker',
        width: 90,
        pinned: 'left',
        cellRenderer: (params: { value: string }) => (
          <a
            href={`https://finance.yahoo.com/quote/${params.value}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#0066cc', textDecoration: 'none', fontWeight: 'bold' }}
          >
            {params.value}
          </a>
        ),
      },
      {
        headerName: 'Entry Date',
        field: 'entry_date',
        width: 110,
        valueFormatter: (params: ValueFormatterParams) => formatDate(params.value),
      },
      {
        headerName: 'Entry',
        field: 'entry_price',
        width: 85,
        valueFormatter: (params: ValueFormatterParams) => `$${params.value?.toFixed(2)}`,
      },
      {
        headerName: 'Current',
        field: 'current_price',
        width: 85,
        valueFormatter: (params: ValueFormatterParams) => `$${params.value?.toFixed(2)}`,
      },
      {
        headerName: 'P&L %',
        field: 'current_pnl_pct',
        width: 85,
        valueFormatter: (params: ValueFormatterParams) => formatPercent(params.value ?? 0),
        cellClass: (params: CellClassParams) =>
          params.value >= 0 ? 'cell-positive' : 'cell-negative',
      },
      {
        headerName: 'P&L $',
        field: 'current_pnl_dollars',
        width: 95,
        valueFormatter: (params: ValueFormatterParams) => formatCurrency(params.value ?? 0),
        cellClass: (params: CellClassParams) =>
          params.value >= 0 ? 'cell-positive' : 'cell-negative',
      },
      {
        headerName: 'Days',
        field: 'hold_days',
        width: 65,
      },
      {
        headerName: 'Score',
        field: 'entry_score',
        width: 75,
        valueFormatter: (params: ValueFormatterParams) => params.value?.toFixed(1),
        sort: 'desc',
      },
      {
        headerName: 'RSI2',
        field: 'entry_rsi2',
        width: 70,
        valueFormatter: (params: ValueFormatterParams) => params.value?.toFixed(1),
      },
      {
        headerName: 'RS%',
        field: 'entry_rs_vs_spy',
        width: 75,
        valueFormatter: (params: ValueFormatterParams) => formatPercent(params.value ?? 0),
      },
      {
        headerName: 'Sector',
        field: 'sector',
        width: 140,
      },
      {
        headerName: 'Status',
        field: 'status',
        width: 120,
        cellRenderer: (params: { data: OpenPosition }) => {
          if (params.data.status === 'pending_close') {
            const isAcknowledged = acknowledgedIds.has(params.data.id);
            if (isAcknowledged) {
              return <span className="status-acknowledged">Acknowledged</span>;
            }
            return (
              <button
                className="ack-btn"
                onClick={() => onAcknowledge(params.data.id)}
              >
                Acknowledge
              </button>
            );
          }
          return <span className="status-open">Open</span>;
        },
      },
    ];

    if (showInTop20Column) {
      cols.splice(2, 0, {
        headerName: 'Top 20',
        field: 'in_top20',
        width: 80,
        cellRenderer: (params: { value: boolean }) =>
          params.value
            ? <span className="badge-yes">Yes</span>
            : <span className="badge-no">No</span>,
      });
    }

    return cols;
  }, [showInTop20Column, acknowledgedIds, onAcknowledge]);

  const getRowClass = useCallback((params: { data: OpenPosition }) => {
    if (params.data.status === 'pending_close') {
      return 'row-pending-close';
    }
    return '';
  }, []);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    resizable: true,
  }), []);

  return (
    <div className="ag-theme-alpine grid-container">
      <AgGridReact
        rowData={positions}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        getRowClass={getRowClass}
        domLayout="autoHeight"
        animateRows={true}
      />
    </div>
  );
}

interface ClosedPositionGridProps {
  positions: ClosedPosition[];
  showWasTop20Column?: boolean;
}

export function ClosedPositionGrid({
  positions,
  showWasTop20Column = false
}: ClosedPositionGridProps) {

  const columnDefs = useMemo<ColDef<ClosedPosition>[]>(() => {
    const cols: ColDef<ClosedPosition>[] = [
      {
        headerName: '#',
        valueGetter: (params) => params.node?.rowIndex != null ? params.node.rowIndex + 1 : '',
        width: 50,
        pinned: 'left',
      },
      {
        headerName: 'Ticker',
        field: 'ticker',
        width: 90,
        pinned: 'left',
        cellRenderer: (params: { value: string }) => (
          <a
            href={`https://finance.yahoo.com/quote/${params.value}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#0066cc', textDecoration: 'none', fontWeight: 'bold' }}
          >
            {params.value}
          </a>
        ),
      },
      {
        headerName: 'Entry',
        field: 'entry_date',
        width: 100,
        valueFormatter: (params: ValueFormatterParams) => formatDate(params.value),
      },
      {
        headerName: 'Exit',
        field: 'exit_date',
        width: 100,
        valueFormatter: (params: ValueFormatterParams) => formatDate(params.value),
        sort: 'desc',
      },
      {
        headerName: 'Entry $',
        field: 'entry_price',
        width: 85,
        valueFormatter: (params: ValueFormatterParams) => `$${params.value?.toFixed(2)}`,
      },
      {
        headerName: 'Exit $',
        field: 'exit_price',
        width: 85,
        valueFormatter: (params: ValueFormatterParams) => `$${params.value?.toFixed(2)}`,
      },
      {
        headerName: 'P&L %',
        field: 'pnl_pct',
        width: 85,
        valueFormatter: (params: ValueFormatterParams) => formatPercent(params.value ?? 0),
        cellClass: (params: CellClassParams) =>
          params.value >= 0 ? 'cell-positive' : 'cell-negative',
      },
      {
        headerName: 'P&L $',
        field: 'pnl_dollars',
        width: 95,
        valueFormatter: (params: ValueFormatterParams) => formatCurrency(params.value ?? 0),
        cellClass: (params: CellClassParams) =>
          params.value >= 0 ? 'cell-positive' : 'cell-negative',
      },
      {
        headerName: 'Days',
        field: 'hold_days',
        width: 65,
      },
      {
        headerName: 'Exit Reason',
        field: 'exit_reason',
        width: 130,
      },
      {
        headerName: 'Score',
        field: 'entry_score',
        width: 75,
        valueFormatter: (params: ValueFormatterParams) => params.value?.toFixed(1),
      },
      {
        headerName: 'Sector',
        field: 'sector',
        width: 140,
      },
    ];

    if (showWasTop20Column) {
      cols.splice(2, 0, {
        headerName: 'Was Top 20',
        field: 'was_in_top20',
        width: 95,
        cellRenderer: (params: { value: boolean }) =>
          params.value
            ? <span className="badge-yes">Yes</span>
            : <span className="badge-no">No</span>,
      });
    }

    return cols;
  }, [showWasTop20Column]);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    resizable: true,
  }), []);

  return (
    <div className="ag-theme-alpine grid-container">
      <AgGridReact
        rowData={positions}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        domLayout="autoHeight"
        animateRows={true}
      />
    </div>
  );
}
