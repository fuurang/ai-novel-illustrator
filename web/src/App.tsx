import { BrowserRouter, Routes, Route, Outlet, useLocation } from 'react-router-dom'
import Sidebar from '@/components/Sidebar'
import TopBar from '@/components/TopBar'
import Home from '@/pages/Home'
import ProjectDetail from '@/pages/ProjectDetail'
import Settings from '@/pages/Settings'
import Prompts from '@/pages/Prompts'
import { useProjectStore } from '@/stores/projectStore'
import { useTheme } from '@/hooks/useTheme'
import { useEffect } from 'react'

function Layout() {
  const fetchProjects = useProjectStore((s) => s.fetchProjects)
  const { theme } = useTheme()
  const location = useLocation()
  const isProjectDetail = location.pathname.startsWith('/project/')

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  return (
    <div className="h-screen overflow-hidden flex bg-base">
      {!isProjectDetail && <Sidebar />}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/project/:id" element={<ProjectDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/prompts" element={<Prompts />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
