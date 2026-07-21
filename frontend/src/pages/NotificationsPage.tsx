import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getSchedule, listNotifications, sendNow, setSchedule } from '../api/notifications'
import { useAuth } from '../lib/auth'
import { IconBell, IconMail, IconClock } from '../components/icons'

export function NotificationsPage() {
  const qc = useQueryClient()
  const { user } = useAuth()
  const { data: notifications, isLoading } = useQuery({ queryKey: ['notifications'], queryFn: listNotifications })
  const { data: schedule } = useQuery({ queryKey: ['schedule'], queryFn: getSchedule })

  const [frequency, setFrequency] = useState<'daily' | 'weekly'>('daily')
  const [time, setTime] = useState('08:00')

  useEffect(() => {
    if (schedule) {
      setFrequency(schedule.frequency)
      setTime(schedule.time)
    }
  }, [schedule])

  const send = useMutation({ mutationFn: sendNow, onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })
  const save = useMutation({
    mutationFn: () => setSchedule({ frequency, time, timezone: 'Africa/Ouagadougou' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedule'] }),
  })

  const keywords = user?.keywords ?? []
  const activeCount = schedule?.is_active ? 1 : 0

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-3xl font-extrabold text-ink">Alertes</h1>
          <span className="rounded-full bg-navy/5 px-3 py-1 text-sm font-semibold text-navy">
            {activeCount} active{activeCount > 1 ? 's' : ''}
          </span>
        </div>
        <button
          onClick={() => send.mutate()}
          disabled={send.isPending}
          className="flex items-center gap-2 rounded-xl bg-orange px-5 py-2.5 text-sm font-semibold text-white hover:bg-orange-dark disabled:opacity-60"
        >
          <IconMail className="h-4 w-4" />
          {send.isPending ? 'Envoi…' : 'Envoyer un rapport maintenant'}
        </button>
      </div>

      {send.data && (
        <p className="mt-4 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">
          {send.data.count} appel(s) d'offres · {send.data.emailed ? 'Email envoyé' : 'Aucun destinataire email'}
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* left: active alert + history */}
        <div className="flex flex-col gap-4 lg:col-span-2">
          {/* the configured watch, shown as an alert card */}
          <div className="rounded-2xl border border-line bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-display text-lg font-bold text-ink">Rapport de veille</h3>
                <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
                  <IconClock className="h-4 w-4 text-muted-soft" />
                  {schedule
                    ? `${schedule.frequency === 'daily' ? 'Quotidien' : 'Hebdomadaire'} à ${schedule.time} (${schedule.timezone})`
                    : 'Aucune planification configurée'}
                </p>
              </div>
              <span
                className={`relative h-6 w-11 rounded-full ${schedule?.is_active ? 'bg-blue-500' : 'bg-line'}`}
                title={schedule?.is_active ? 'Active' : 'Inactive'}
              >
                <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${schedule?.is_active ? 'left-[22px]' : 'left-0.5'}`} />
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {keywords.length > 0 ? (
                keywords.slice(0, 8).map((k) => (
                  <span key={k} className="rounded-full bg-orange/10 px-3 py-1 text-sm font-medium text-orange">
                    {k}
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted">
                  Aucun mot-clé.{' '}
                  <Link to="/settings" className="font-semibold text-orange hover:underline">
                    Ajoutez-en
                  </Link>
                </span>
              )}
            </div>
          </div>

          <h2 className="mt-2 text-sm font-extrabold uppercase tracking-wide text-ink">Historique des envois</h2>
          {isLoading && <p className="text-muted">Chargement…</p>}
          {!isLoading && notifications?.length === 0 && (
            <div className="rounded-2xl border border-dashed border-line bg-white p-8 text-center text-muted">
              Aucun rapport envoyé pour l'instant.
            </div>
          )}
          {notifications?.map((n) => (
            <div key={n.id} className="flex items-center justify-between rounded-xl border border-line bg-white p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy/5 text-navy">
                  <IconBell className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-ink">Rapport · {n.tender_ids.length} appel(s) d'offres</p>
                  <p className="text-xs text-muted-soft">{new Date(n.created_at).toLocaleString('fr-FR')}</p>
                </div>
              </div>
              {!n.seen && <span className="h-2.5 w-2.5 rounded-full bg-orange" title="Non lu" />}
            </div>
          ))}
        </div>

        {/* right: config panel */}
        <div className="rounded-2xl border border-line bg-white p-6 shadow-sm">
          <h2 className="font-display text-xl font-bold text-ink">Configurer l'alerte</h2>
          <p className="mt-1 text-sm text-muted">Réglez vos critères pour ne manquer aucune opportunité.</p>

          <div className="mt-6">
            <p className="text-sm font-bold text-ink">Mots-clés surveillés</p>
            <div className="mt-2 flex min-h-[3rem] flex-wrap gap-2 rounded-xl border border-line p-3">
              {keywords.length > 0 ? (
                keywords.map((k) => (
                  <span key={k} className="rounded-md bg-orange/10 px-2.5 py-1 text-sm text-orange">
                    {k}
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted-soft">Aucun mot-clé configuré.</span>
              )}
            </div>
            <Link to="/settings" className="mt-2 inline-block text-xs font-semibold text-orange hover:underline">
              Modifier les mots-clés dans Paramètres →
            </Link>
          </div>

          <div className="mt-6">
            <p className="text-sm font-bold text-ink">Fréquence de notification</p>
            <div className="mt-3 flex flex-col gap-3">
              {([
                { v: 'daily', label: 'Quotidienne' },
                { v: 'weekly', label: 'Hebdomadaire' },
              ] as const).map((opt) => (
                <label key={opt.v} className="flex cursor-pointer items-center gap-3 text-sm text-ink">
                  <input
                    type="radio"
                    name="freq"
                    checked={frequency === opt.v}
                    onChange={() => setFrequency(opt.v)}
                    className="h-4 w-4 accent-orange"
                  />
                  {opt.label}
                </label>
              ))}
            </div>
            <label className="mt-4 flex flex-col gap-1.5 text-sm font-bold text-ink">
              Heure d'envoi
              <input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="rounded-lg border border-line px-3 py-2.5 text-base font-normal outline-none focus:border-orange focus:ring-2 focus:ring-orange/15"
              />
            </label>
          </div>

          <div className="mt-6 rounded-xl bg-gray-50 p-3 text-xs text-muted">
            Fuseau : Africa/Ouagadougou (GMT+0)
          </div>

          {save.isSuccess && <p className="mt-4 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">Planification enregistrée.</p>}
          {save.isError && <p className="mt-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">Échec de l'enregistrement.</p>}

          <button
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="mt-6 w-full rounded-xl bg-orange py-3 text-sm font-semibold text-white hover:bg-orange-dark disabled:opacity-60"
          >
            {save.isPending ? 'Enregistrement…' : "Enregistrer l'alerte"}
          </button>
        </div>
      </div>
    </div>
  )
}
