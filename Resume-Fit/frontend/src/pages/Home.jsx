import React from 'react'
import { Link } from 'react-router-dom'
import { FileText, Zap, Target, Download } from 'lucide-react'

function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-indigo-600">Resume-Fit</h1>
          <Link
            to="/generate"
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
          >
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <main className="max-w-7xl mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold text-gray-900 mb-6">
            AI-Powered Resume Tailoring
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
            Paste a job description, get an ATS-optimized resume tailored to the role.
            Powered by Claude (writer) and GPT-4 (scorer) agents.
          </p>
          <Link
            to="/generate"
            className="inline-flex items-center bg-indigo-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-indigo-700 transition shadow-lg"
          >
            <Zap className="mr-2" size={24} />
            Generate Resume
          </Link>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <div className="bg-white p-6 rounded-xl shadow-md">
            <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
              <FileText className="text-indigo-600" size={24} />
            </div>
            <h3 className="text-xl font-semibold mb-2">Multi-Agent System</h3>
            <p className="text-gray-600">
              Claude writes, GPT-4 scores. Iterative refinement until quality threshold is met.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-md">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <Target className="text-green-600" size={24} />
            </div>
            <h3 className="text-xl font-semibold mb-2">Strict ATS Scoring</h3>
            <p className="text-gray-600">
              Not just keyword matching. Requires evidence in work experience bullets.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-md">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <Download className="text-purple-600" size={24} />
            </div>
            <h3 className="text-xl font-semibold mb-2">Download Ready</h3>
            <p className="text-gray-600">
              Get DOCX and PDF files with exact formatting, ready to submit.
            </p>
          </div>
        </div>

        {/* How it works */}
        <div className="bg-white rounded-xl shadow-md p-8">
          <h3 className="text-2xl font-bold text-center mb-8">How It Works</h3>
          <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            <div className="text-center flex-1">
              <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-indigo-600">
                1
              </div>
              <h4 className="font-semibold mb-2">Paste Job Description</h4>
              <p className="text-gray-600 text-sm">Copy the full JD from any job posting</p>
            </div>
            
            <div className="hidden md:block text-4xl text-gray-300">→</div>
            
            <div className="text-center flex-1">
              <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-indigo-600">
                2
              </div>
              <h4 className="font-semibold mb-2">AI Generates & Scores</h4>
              <p className="text-gray-600 text-sm">Claude writes, GPT-4 scores, loop until 85+</p>
            </div>
            
            <div className="hidden md:block text-4xl text-gray-300">→</div>
            
            <div className="text-center flex-1">
              <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-indigo-600">
                3
              </div>
              <h4 className="font-semibold mb-2">Download & Apply</h4>
              <p className="text-gray-600 text-sm">Get DOCX/PDF, preview live, submit</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-600">
          <p>Built by Srikanth Manchimchetty</p>
          <p className="text-sm mt-2">
            <a href="https://github.com/Srikanthsanju/Resume-Fit" className="text-indigo-600 hover:underline">
              GitHub
            </a>
            {' · '}
            <a href="https://www.linkedin.com/in/srikanthmanchimchetty" className="text-indigo-600 hover:underline">
              LinkedIn
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}

export default Home
