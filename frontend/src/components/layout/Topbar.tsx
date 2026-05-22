interface Props {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export default function Topbar({ title, subtitle, actions }: Props) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-xl font-bold text-textMain">{title}</h1>
        {subtitle && <p className="text-sm text-textMuted mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
