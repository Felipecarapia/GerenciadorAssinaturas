import { flexRender, getCoreRowModel, getPaginationRowModel, getSortedRowModel, useReactTable, type ColumnDef, type RowData, type SortingState } from '../lib/table'
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Button } from './ui/button'
import { Card } from './ui/card'

export function DataTable<T extends RowData>({ data, columns, empty = 'Nenhum registro encontrado.', pageSize = 8, label = 'Resultados' }: { data: T[]; columns: ColumnDef<T>[]; empty?: string; pageSize?: number; label?: string }) {
  const [sorting, setSorting] = useState<SortingState>([])
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageIndex: 0, pageSize } },
  })
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto" role="region" aria-label={label} tabIndex={0}>
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <caption className="sr-only">{label}. {data.length} {data.length === 1 ? 'registro' : 'registros'}.</caption>
          <thead className="bg-muted/75 text-xs uppercase tracking-wide text-muted-foreground">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} aria-sort={header.column.getCanSort() ? (header.column.getIsSorted() === 'asc' ? 'ascending' : header.column.getIsSorted() === 'desc' ? 'descending' : 'none') : undefined} className="h-11 border-b border-border px-4 font-semibold">
                    {header.isPlaceholder ? null : (
                      header.column.getCanSort() ? <button className="inline-flex min-h-8 items-center gap-1.5 whitespace-nowrap rounded-md text-left hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" onClick={header.column.getToggleSortingHandler()}>
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() === 'asc' ? <ArrowUp aria-hidden="true" className="size-3.5" /> : header.column.getIsSorted() === 'desc' ? <ArrowDown aria-hidden="true" className="size-3.5" /> : <ArrowUpDown aria-hidden="true" className="size-3.5 opacity-45" />}
                      </button> : flexRender(header.column.columnDef.header, header.getContext())
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="h-12 border-b border-border/70 transition-colors last:border-0 hover:bg-muted/45">
                {row.getVisibleCells().map((cell) => <td key={cell.id} className="px-4 py-2.5 align-middle">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        {!data.length && <div className="flex min-h-36 items-center justify-center text-sm text-muted-foreground">{empty}</div>}
      </div>
      {data.length > pageSize && (
        <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground">
          <span aria-live="polite">{table.getState().pagination.pageIndex * pageSize + 1}–{Math.min((table.getState().pagination.pageIndex + 1) * pageSize, data.length)} de {data.length}</span>
          <div className="flex gap-1">
            <Button size="icon" variant="ghost" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()} aria-label="Página anterior"><ChevronLeft className="size-4" /></Button>
            <Button size="icon" variant="ghost" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()} aria-label="Próxima página"><ChevronRight className="size-4" /></Button>
          </div>
        </div>
      )}
    </Card>
  )
}
