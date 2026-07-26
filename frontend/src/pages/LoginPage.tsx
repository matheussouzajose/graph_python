import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Eye,
  EyeOff,
  LockKeyhole,
  Loader2,
  Mail,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSignIn } from '@/lib/auth-kit-core'
import { login } from '@/lib/api'
import { setStoredAccessToken } from '@/lib/auth-token'
import { cn } from '@/lib/utils'
import type { AuthUser } from '@/types/api'

const pulseRows = [
  { label: 'Receita prevista', value: 'R$ 84,7k', width: 'w-[86%]', tone: 'bg-teal-500' },
  { label: 'Clientes em alta', value: '+128', width: 'w-[68%]', tone: 'bg-blue-500' },
  { label: 'Ações priorizadas', value: '42', width: 'w-[53%]', tone: 'bg-amber-500' },
]

const liveEvents = [
  'Pedido recorrente detectado',
  'Produto com ruptura em 9 dias',
  'Cliente premium voltou a comprar',
  'Campanha com ROAS acima da média',
]

export function LoginPage() {
  const navigate = useNavigate()
  const signIn = useSignIn<AuthUser>()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await login(email, password)
      const authUser: AuthUser = {
        id: response.user.id,
        company_id: response.user.company_id,
        email: response.user.email,
        name: response.user.name,
        role: response.user.role,
      }

      const signed = signIn({
        auth: {
          token: response.access_token,
          type: 'Bearer',
        },
        userState: authUser,
      })

      if (!signed) {
        throw new Error('Não foi possível iniciar a sessão.')
      }

      setStoredAccessToken(response.access_token)
      navigate('/', { replace: true })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao entrar'
      toast.error('Falha no login', { description: message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="relative min-h-svh overflow-hidden bg-[#f7f7f2] text-slate-950">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(20,184,166,0.16),transparent_30%),radial-gradient(circle_at_82%_12%,rgba(245,158,11,0.14),transparent_26%),linear-gradient(135deg,rgba(15,23,42,0.04),transparent_38%)]" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-slate-300 to-transparent" />

      <section className="relative mx-auto grid min-h-svh w-full max-w-7xl items-center gap-10 px-4 py-6 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-8">
        <div className="flex min-h-[560px] flex-col justify-between rounded-[2rem] border border-white/70 bg-slate-950 p-5 text-white shadow-2xl shadow-slate-950/20 sm:p-7 lg:min-h-[720px]">
          <header className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-white text-slate-950 shadow-lg shadow-teal-500/20">
                <Sparkles className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">Oráculo</p>
                <p className="text-xs text-white/50">Inteligência comercial</p>
              </div>
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs text-white/70 sm:flex">
              <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.9)]" />
              Sincronizado agora
            </div>
          </header>

          <div className="grid gap-6 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:items-end">
            <div className="max-w-xl space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-3 py-1.5 text-xs font-medium text-teal-100">
                <Zap className="size-3.5" />
                Painel vivo de crescimento
              </div>
              <div className="space-y-4">
                <h1 className="max-w-2xl text-4xl font-semibold leading-[0.98] tracking-normal sm:text-5xl lg:text-6xl">
                  Decida a próxima venda antes que ela esfrie.
                </h1>
                <p className="max-w-lg text-sm leading-6 text-white/58 sm:text-base">
                  Recomendações, clientes em risco, produtos acelerando e sinais de receita em uma
                  operação que muda junto com seus dados.
                </p>
              </div>
            </div>

            <div className="relative min-h-[360px]">
              <div className="absolute left-1/2 top-10 h-52 w-52 -translate-x-1/2 rounded-full bg-teal-400/18 blur-3xl" />

              <div className="login-float relative ml-auto max-w-sm rounded-[1.5rem] border border-white/12 bg-white/[0.08] p-4 shadow-2xl shadow-black/35 backdrop-blur-xl">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="text-xs text-white/45">Hoje</p>
                    <p className="text-xl font-semibold">Performance comercial</p>
                  </div>
                  <div className="flex size-10 items-center justify-center rounded-2xl bg-teal-300 text-slate-950">
                    <BarChart3 className="size-5" />
                  </div>
                </div>

                <div className="space-y-4">
                  {pulseRows.map((row, index) => (
                    <div key={row.label} className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-white/56">{row.label}</span>
                        <span className="font-medium text-white">{row.value}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/10">
                        <div
                          className={cn('login-bar h-full rounded-full', row.tone, row.width)}
                          style={{ animationDelay: `${index * 240}ms` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 grid grid-cols-3 gap-2">
                  <MetricPill label="Conversão" value="+18%" />
                  <MetricPill label="Ticket" value="R$ 412" />
                  <MetricPill label="Alertas" value="7" />
                </div>
              </div>

              <div className="login-slide absolute bottom-4 left-0 w-[88%] max-w-sm rounded-2xl border border-white/12 bg-white/[0.09] p-3 shadow-2xl shadow-black/30 backdrop-blur-xl">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-amber-300 text-slate-950">
                    <TrendingUp className="size-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs text-white/45">Sinal ativo</p>
                    <div className="h-5 overflow-hidden">
                      <div className="login-ticker space-y-1">
                        {liveEvents.concat(liveEvents[0]).map((event, index) => (
                          <p key={`${event}-${index}`} className="truncate text-sm font-medium">
                            {event}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <footer className="grid gap-3 border-t border-white/10 pt-5 text-xs text-white/55 sm:grid-cols-3">
            <FooterSignal icon={ShieldCheck} text="Acesso protegido" />
            <FooterSignal icon={BadgeCheck} text="Dados por empresa" />
            <FooterSignal icon={Sparkles} text="IA aplicada a vendas" />
          </footer>
        </div>

        <div className="mx-auto w-full max-w-md lg:pr-4">
          <div className="mb-8 flex items-center justify-between lg:hidden">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-slate-950 text-white">
                <Sparkles className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">Oráculo</p>
                <p className="text-xs text-slate-500">Inteligência comercial</p>
              </div>
            </div>
          </div>

          <div className="rounded-[1.75rem] border border-slate-200/80 bg-white/80 p-2 shadow-2xl shadow-slate-950/10 backdrop-blur-xl">
            <div className="rounded-[1.35rem] border border-slate-100 bg-white p-5 sm:p-7">
              <div className="mb-8 space-y-3">
                <div className="flex size-11 items-center justify-center rounded-2xl bg-slate-950 text-white">
                  <LockKeyhole className="size-5" />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold tracking-normal">Entrar na conta</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Continue para sua central de inteligência comercial.
                  </p>
                </div>
              </div>

              <form className="space-y-5" onSubmit={onSubmit}>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-700">
                    E-mail
                  </Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className="h-12 rounded-xl border-slate-200 bg-slate-50 pl-10 text-[15px] shadow-inner shadow-slate-950/[0.02] focus-visible:bg-white"
                      placeholder="voce@empresa.com"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-700">
                    Senha
                  </Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="h-12 rounded-xl border-slate-200 bg-slate-50 pl-10 pr-11 text-[15px] shadow-inner shadow-slate-950/[0.02] focus-visible:bg-white"
                      placeholder="Sua senha"
                      required
                    />
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                      onClick={() => setShowPassword((current) => !current)}
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    >
                      {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  className="h-12 w-full rounded-xl bg-slate-950 text-[15px] text-white shadow-lg shadow-slate-950/15 hover:bg-slate-800"
                  disabled={loading}
                >
                  {loading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <ArrowRight className="size-4" />
                  )}
                  Entrar
                </Button>
              </form>
            </div>
          </div>

          <p className="mt-5 text-center text-xs text-slate-500">
            Ambiente seguro para dados comerciais e integrações conectadas.
          </p>
        </div>
      </section>
    </main>
  )
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.07] p-3">
      <p className="truncate text-[11px] text-white/45">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
    </div>
  )
}

function FooterSignal({ icon: Icon, text }: { icon: typeof ShieldCheck; text: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Icon className="size-4 shrink-0 text-teal-200" />
      <span className="truncate">{text}</span>
    </div>
  )
}
