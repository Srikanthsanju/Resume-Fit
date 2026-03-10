import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Loader2, Download, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'
import api from '../services/api'

function Generate() {
  const [jobDescription, setJobDescription] = useState('')
  const [roleType, setRoleType] = useState('AI Engineer')
  const [jobType, setJobType] = useState('Fulltime')
  const [companyName, setCompanyName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [previewHtml, setPreviewHtml] = useState('')
  const [error, setError] = useState('')
  
  // Load empty preview on mount
  useEffect(() => {
    loadEmptyPreview()
  }, [])
  
  const loadEmptyPreview = async () => {
    try {
      const response = await api.get('/api/preview/empty')
      setPreviewHtml(response.data.html)
    } catch (err) {
      console.error('Failed to load empty preview')
    }
  }
  
  const updatePreview = async (resumeContent) => {
    try {
      const response = await api.post('/api/preview', {
        resume_content: resumeContent,
        mode: jobType
      })
      setPreviewHtml(response.data.html)
    } catch (err) {
      console.error('Failed to update preview')
    }
  }
  
  const handleGenerate = async () => {
    if (!jobDescription.trim()) {
      setError('Please paste a job description')
      return
    }
    
    setLoading(true)
    setError('')
    setResult(null)
    
    try {
      const response = await api.post('/api/generate', {
        job_description: jobDescription,
        role_type: roleType,
        job_type: jobType,
        company_name: companyName || null,
        job_title: jobTitle || null
      })
      
      setResult(response.data)
      
      // Update preview with generated content
      if (response.data.resume_content) {
        await updatePreview(response.data.resume_content)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed. Check API keys.')
    } finally {
      setLoading(false)
    }
  }
  
  const handleQuickPreview = async () => {
    if (!jobDescription.trim()) {
      setError('Please paste a job description')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const response = await api.post('/api/generate/quick-preview', {
        job_description: jobDescription,
        role_type: roleType,
        job_type: jobType
      })
      
      if (response.data.resume_content) {
        await updatePreview(response.data.resume_content)
      }
    } catch (err) {
      setError('Quick preview failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-600 hover:text-gray-900">
              <ArrowLeft size={24} />
            </Link>
            <h1 className="text-xl font-bold text-indigo-600">Resume-Fit</h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Left Column - Input */}
          <div className="space-y-4">
            {/* Job Description */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-3">Job Description</h2>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here..."
                className="w-full h-64 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            
            {/* Settings */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-3">Settings</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Role Type</label>
                  <select
                    value={roleType}
                    onChange={(e) => setRoleType(e.target.value)}
                    className="w-full p-2 border rounded-lg"
                  >
                    <option>AI Engineer</option>
                    <option>Data Scientist</option>
                    <option>Software Engineer</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Job Type</label>
                  <select
                    value={jobType}
                    onChange={(e) => setJobType(e.target.value)}
                    className="w-full p-2 border rounded-lg"
                  >
                    <option>Fulltime</option>
                    <option>Contract</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Company Name</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g., Google"
                    className="w-full p-2 border rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Job Title</label>
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="e.g., Senior AI Engineer"
                    className="w-full p-2 border rounded-lg"
                  />
                </div>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin" size={20} />
                    Generating...
                  </>
                ) : (
                  <>
                    <RefreshCw size={20} />
                    Generate Resume
                  </>
                )}
              </button>
              <button
                onClick={handleQuickPreview}
                disabled={loading}
                className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Quick Preview
              </button>
            </div>
            
            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg flex items-center gap-2">
                <AlertCircle size={20} />
                {error}
              </div>
            )}
            
            {/* Result */}
            {result && (
              <div className="bg-white rounded-lg shadow p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Generation Complete</h2>
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                    result.passed ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {result.passed ? (
                      <span className="flex items-center gap-1">
                        <CheckCircle size={16} /> Passed
                      </span>
                    ) : (
                      'Best Effort'
                    )}
                  </div>
                </div>
                
                {/* Score */}
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-indigo-600">{result.final_score}</div>
                    <div className="text-sm text-gray-500">Score</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-semibold">{result.iterations}</div>
                    <div className="text-sm text-gray-500">Iterations</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium capitalize">{result.score_details?.ats_confidence || 'N/A'}</div>
                    <div className="text-sm text-gray-500">ATS Conf.</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm font-medium capitalize">{result.score_details?.recruiter_confidence || 'N/A'}</div>
                    <div className="text-sm text-gray-500">Recruiter Conf.</div>
                  </div>
                </div>
                
                {/* Downloads */}
                <div className="flex gap-3">
                  {result.docx_url && (
                    <a
                      href={result.docx_url}
                      download
                      className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-center hover:bg-blue-700 flex items-center justify-center gap-2"
                    >
                      <Download size={18} />
                      Download DOCX
                    </a>
                  )}
                  {result.pdf_url && (
                    <a
                      href={result.pdf_url}
                      download
                      className="flex-1 bg-green-600 text-white py-2 rounded-lg text-center hover:bg-green-700 flex items-center justify-center gap-2"
                    >
                      <Download size={18} />
                      Download PDF
                    </a>
                  )}
                </div>
                
                {/* Feedback */}
                {result.score_details?.top_fixes?.length > 0 && (
                  <div>
                    <h3 className="font-medium mb-2">Improvement Suggestions</h3>
                    <ul className="text-sm text-gray-600 space-y-1">
                      {result.score_details.top_fixes.slice(0, 3).map((fix, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-yellow-500">•</span>
                          {fix}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Right Column - Live Preview */}
          <div className="bg-white rounded-lg shadow">
            <div className="border-b px-4 py-3 flex items-center justify-between">
              <h2 className="font-semibold">Live Preview</h2>
              <span className="text-sm text-gray-500">{jobType} Format</span>
            </div>
            <div 
              className="p-4 overflow-auto" 
              style={{ height: 'calc(100vh - 200px)' }}
            >
              <div 
                className="border rounded-lg shadow-sm overflow-hidden bg-white"
                style={{ 
                  transform: 'scale(0.85)', 
                  transformOrigin: 'top left',
                  width: '117.6%'  // 100 / 0.85
                }}
              >
                <iframe
                  srcDoc={previewHtml}
                  title="Resume Preview"
                  className="w-full border-0"
                  style={{ height: '1200px' }}
                />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Generate
