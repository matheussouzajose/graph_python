import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bot,
  Boxes,
  Compass,
  Home,
  Package,
  ReceiptText,
  Search,
  Settings,
  Sparkles,
  Users,
} from 'lucide-react'
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command'

const NAV_COMMANDS = [
  { label: 'Home', path: '/', icon: Home, shortcut: 'H' },
  { label: 'Pedidos', path: '/pedidos', icon: ReceiptText, shortcut: 'P' },
  { label: 'Produtos', path: '/produtos', icon: Package, shortcut: 'R' },
  { label: 'Catálogo ERP', path: '/catalogo-produtos', icon: Boxes, shortcut: 'C' },
  { label: 'Clientes', path: '/clientes', icon: Users, shortcut: 'L' },
  { label: 'Recomendações', path: '/recomendacoes', icon: Sparkles, shortcut: 'M' },
  { label: 'Oráculo', path: '/oraculo', icon: Compass, shortcut: 'O' },
  { label: 'Agentes', path: '/agentes', icon: Bot, shortcut: 'A' },
  { label: 'Configurações', path: '/configuracoes', icon: Settings, shortcut: 'S' },
] as const

const ASK_COMMANDS = [
  'Quais produtos mais venderam?',
  'Quais clientes estão em risco?',
  'Quais oportunidades de cross-sell existem?',
] as const

export function GlobalCommandMenu({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        onOpenChange(!open)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onOpenChange, open])

  function go(path: string) {
    navigate(path)
    onOpenChange(false)
  }

  function ask(question: string) {
    navigate('/oraculo', { state: { question } })
    onOpenChange(false)
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Comandos"
      description="Navegue e dispare ações rápidas."
      className="max-w-2xl rounded-3xl border bg-card/96 shadow-2xl shadow-slate-950/20 backdrop-blur-xl"
    >
      <Command className="rounded-3xl">
        <CommandInput placeholder="Buscar tela, ação ou pergunta..." />
        <CommandList className="max-h-[28rem]">
          <CommandEmpty>Nenhum comando encontrado.</CommandEmpty>
          <CommandGroup heading="Navegação">
            {NAV_COMMANDS.map(({ label, path, icon: Icon, shortcut }) => (
              <CommandItem key={path} value={`${label} ${path}`} onSelect={() => go(path)}>
                <Icon className="size-4 text-primary" />
                <span>{label}</span>
                <CommandShortcut>{shortcut}</CommandShortcut>
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Perguntar ao Oráculo">
            {ASK_COMMANDS.map((question) => (
              <CommandItem key={question} value={question} onSelect={() => ask(question)}>
                <Search className="size-4 text-primary" />
                <span>{question}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
