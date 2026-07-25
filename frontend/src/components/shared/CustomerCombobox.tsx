import { useState } from 'react'
import { Check, ChevronsUpDown, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import type { CustomerSummary } from '@/types/api'

interface CustomerComboboxProps {
  customers: CustomerSummary[]
  value: string | null
  onChange: (customerId: string) => void
  loading?: boolean
  placeholder?: string
}

export function CustomerCombobox({
  customers,
  value,
  onChange,
  loading,
  placeholder = 'Selecione um cliente…',
}: CustomerComboboxProps) {
  const [open, setOpen] = useState(false)
  const selected = customers.find((c) => c.customer_id === value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal sm:w-80"
          disabled={loading}
        >
          <span className="flex min-w-0 items-center gap-2 truncate">
            <User className="size-4 shrink-0 text-muted-foreground" />
            {selected ? (
              <span className="truncate">{selected.name ?? selected.customer_id}</span>
            ) : (
              <span className="text-muted-foreground">
                {loading ? 'Carregando clientes…' : placeholder}
              </span>
            )}
          </span>
          <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0">
        <Command>
          <CommandInput placeholder="Buscar por nome…" />
          <CommandList>
            <CommandEmpty>Nenhum cliente encontrado.</CommandEmpty>
            <CommandGroup>
              {customers.map((customer) => (
                <CommandItem
                  key={customer.customer_id}
                  value={customer.name ?? customer.customer_id}
                  onSelect={() => {
                    onChange(customer.customer_id)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      'size-4',
                      value === customer.customer_id ? 'opacity-100' : 'opacity-0',
                    )}
                  />
                  <span className="truncate">{customer.name ?? customer.customer_id}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
