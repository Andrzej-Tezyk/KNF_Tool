# KNF Tool - Financial Regulatory Research Assistant

## Overview

This is a document analysis and research app designed for working with financial regulatory documentation. By automating the processes of document collection, processing, and information retrieval, this tool significantly reduces the time spent on regulatory research while improving the accuracy and comprehensiveness of findings.

## Purpose

The primary goal of the KNF Tool is to **make it easy to work with regulation documentation and save time on research related to regulations**.

## Technology Stack

### Backend Technologies

**Web Framework & Communication**
- **Flask**: Core web application framework providing RESTful API endpoints and template rendering
- **Flask-SocketIO**: Real-time bidirectional communication for interactive chat features
- **Flask-Caching**: Caching to improve response times and reduce API calls

**AI & Machine Learning**
- **Google Gemini API**: 
  - **Text Embeddings**: Converts document chunks into high-dimensional vector representations for semantic search
  - **Large Language Model**: Generates human-like responses based on retrieved regulatory context
  - **Prompt Enhancement**: Automatically improves user queries for better AI responses

**Vector Database & Search**
- **ChromaDB**: Persistent vector database that stores document embeddings and enables semantic similarity search
- **Asynchronous Processing**: Concurrent document processing for improved performance during database setup

**Document Processing**
- **PDFPlumber**: Robust text extraction from PDF documents with support for complex layouts
- **Text Chunking**: Intelligent document segmentation for optimal embedding generation

**Web Scraping & Data Collection**
- **BeautifulSoup**: HTML parsing for automated document discovery on KNF website
- **Requests**: HTTP client with intelligent retry mechanisms and user agent rotation

## How the RAG System Works

The KNF Tool implements a **Retrieval-Augmented Generation (RAG)** system that combines the power of vector search with large language models to provide accurate, context-aware responses.

### 1. Document Ingestion Pipeline
- **Processing**: Each PDF is processed page by page, with text extracted and cleaned
- **Chunking**: Documents are split into semantically meaningful chunks (typically 1-2 pages)
- **Vector Conversion**: Each chunk is converted to a 768-dimensional vector using Gemini's embedding model

### 2. Query Processing & Retrieval
- **Query Understanding**: User questions are converted to vector embeddings for semantic matching
- **Retrieval**: The system finds the most relevant document chunks based on semantic similarity
- **Context Assembly**: Retrieved chunks are combined with the user's question to create a comprehensive prompt
- **Response**: The Gemini LLM generates accurate answers using only the retrieved regulatory context

### 3. Advanced Features
- **Reranking**: A technique that takes the initial search results and reorders them based on more sophisticated relevance scoring, ensuring the most important and contextually relevant documents appear first in the results.
- **Autocut**: An intelligent feature that automatically determines the optimal number of document chunks to include in the AI response context, balancing between providing enough information for comprehensive answers while avoiding overwhelming the model with irrelevant content.