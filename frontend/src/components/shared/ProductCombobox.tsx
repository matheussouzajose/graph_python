import { useState } from 'react'
import { Check, ChevronsUpDown, Package } from 'lucide-react'
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

export interface ProductOption {
  product_id: string
  product_name: string | null
  product_code: string | null
}

interface ProductComboboxProps {
  products: ProductOption[]
  value: string | null
  onChange: (productId: string) => void
  loading?: boolean
  placeholder?: string
}

export function ProductCombobox({
  products,
  value,
  onChange,
  loading,
  placeholder = 'Selecione um produto…',
}: ProductComboboxProps) {
  const [open, setOpen] = useState(false)
  const selected = products.find((p) => p.product_id === value)

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
            <Package className="size-4 shrink-0 text-muted-foreground" />
            {selected ? (
              <span className="truncate">
                {selected.product_name} ({selected.product_code})
              </span>
            ) : (
              <span className="text-muted-foreground">
                {loading ? 'Carregando produtos…' : placeholder}
              </span>
            )}
          </span>
          <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0">
        <Command>
          <CommandInput placeholder="Buscar por nome ou código…" />
          <CommandList>
            <CommandEmpty>Nenhum produto encontrado.</CommandEmpty>
            <CommandGroup>
              {products.map((product) => (
                <CommandItem
                  key={product.product_id}
                  value={`${product.product_name ?? ''} ${product.product_code ?? ''}`}
                  onSelect={() => {
                    onChange(product.product_id)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      'size-4',
                      value === product.product_id ? 'opacity-100' : 'opacity-0',
                    )}
                  />
                  <span className="truncate">
                    {product.product_name} — {product.product_code}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
