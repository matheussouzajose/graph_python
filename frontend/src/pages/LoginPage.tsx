import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, LockKeyhole, Loader2, LogIn, ShieldCheck, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSignIn } from '@/lib/auth-kit-core'
import { login } from '@/lib/api'
import { setStoredAccessToken } from '@/lib/auth-token'
import type { AuthUser } from '@/types/api'

export function LoginPage() {
  const navigate = useNavigate()
  const signIn = useSignIn<AuthUser>()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

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
    <main className="grid min-h-svh bg-background lg:grid-cols-[minmax(420px,0.92fr)_1.08fr]">
      <section className="hidden border-r bg-sidebar text-sidebar-foreground lg:flex lg:flex-col">
        <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-8">
          <div className="flex size-9 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
            <Sparkles className="size-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">Oráculo</p>
            <p className="text-xs text-sidebar-foreground/55">Inteligência comercial</p>
          </div>
        </div>
        <div className="flex flex-1 flex-col justify-between p-8">
          <div className="space-y-8">
            <div className="max-w-md space-y-3">
              <p className="text-sm font-medium text-sidebar-primary">Acesso seguro</p>
              <h1 className="text-3xl font-semibold tracking-tight">
                Dados comerciais, recomendações e clientes em uma operação protegida.
              </h1>
              <p className="text-sm leading-6 text-sidebar-foreground/62">
                Cada usuário acessa somente os dados da própria empresa. O token de sessão acompanha
                as consultas ao dashboard, recomendações e Oráculo.
              </p>
            </div>

            <div className="grid gap-3">
              <div className="flex items-center gap-3 rounded-lg border border-sidebar-border bg-sidebar-accent/55 p-3">
                <ShieldCheck className="size-5 text-sidebar-primary" />
                <div>
                  <p className="text-sm font-medium">Isolamento por empresa</p>
                  <p className="text-xs text-sidebar-foreground/55">Company scope no backend.</p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-sidebar-border bg-sidebar-accent/55 p-3">
                <BarChart3 className="size-5 text-sidebar-primary" />
                <div>
                  <p className="text-sm font-medium">Operação comercial</p>
                  <p className="text-xs text-sidebar-foreground/55">KPIs, RFM e recomendações.</p>
                </div>
              </div>
            </div>
          </div>
          <p className="text-xs text-sidebar-foreground/45">JWT ativo com expiração configurada.</p>
        </div>
      </section>

      <section className="flex items-center justify-center p-4 sm:p-6">
        <Card className="w-full max-w-md border-border/70 shadow-xl shadow-slate-950/5">
          <CardHeader className="space-y-3 pb-4">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15">
              <LockKeyhole className="size-5" />
            </div>
            <div>
              <CardTitle className="text-xl">Entrar no Oráculo</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Use seu e-mail corporativo para acessar o dashboard.
              </p>
            </div>
          </CardHeader>
          <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            <Button className="h-10 w-full" disabled={loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
              Entrar
            </Button>
          </form>
          </CardContent>
        </Card>
      </section>
    </main>
  )
}
