"""
RAG CSV Export + Complete Session Persistence
Save policies in searchable format for RAG retrieval
"""

import pandas as pd
import csv
import hashlib
from io import StringIO
import streamlit as st
import json
import re
# class RAGPolicyExporter:
#     """Export policies to RAG-friendly CSV format"""
    
#     @staticmethod
#     def generate_policy_id(regulation: str, section: str) -> str:
#         """Generate unique policy ID"""
#         # Format: GDPR-ART5-abc123
#         section_clean = section.replace(' ', '').replace('.', '').replace('(', '').replace(')', '')
#         hash_suffix = hashlib.md5(f"{regulation}{section}".encode()).hexdigest()[:6]
#         return f"{regulation.upper()}-{section_clean}-{hash_suffix}"
    
#     @staticmethod
#     def extract_keywords(statement: str, title: str) -> list:
#         """Extract keywords from policy statement"""
#         import re
        
#         # Common stop words
#         stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
#                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
#                      'may', 'shall', 'must', 'should', 'can', 'could', 'will', 'would'}
        
#         # Extract words
#         text = (statement + " " + title).lower()
#         words = re.findall(r'\b[a-z]{4,}\b', text)  # Words 4+ chars
        
#         # Filter and count
#         word_freq = {}
#         for word in words:
#             if word not in stop_words:
#                 word_freq[word] = word_freq.get(word, 0) + 1
        
#         # Return top 10
#         sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
#         return [word for word, _ in sorted_words[:10]]
    
#     @staticmethod
#     def generate_rag_csv(results: dict) -> str:
#         """Generate RAG CSV from processing results"""
        
#         rows = []
#         regulation = results['regulation']
        
#         for policy in results['policies']:
#             policy_id = RAGPolicyExporter.generate_policy_id(
#                 regulation, 
#                 policy['section']
#             )
            
#             keywords = RAGPolicyExporter.extract_keywords(
#                 policy['statement'],
#                 policy['title']
#             )
            
#             row = {
#                 'policy_id': policy_id,
#                 'regulation': regulation,
#                 'section': policy['section'],
#                 'title': policy['title'],
#                 'description': policy['statement'],
#                 'fotl_formula': policy['fotl_formula'],
#                 'keywords': ','.join(keywords),
#                 'conditions': ','.join(policy.get('conditions', [])),
#                 'action': policy.get('action', ''),
#                 'parent_id': '',  # Can be used for hierarchical policies
#                 'created_at': pd.Timestamp.now().isoformat()
#             }
            
#             rows.append(row)
        
#         # Create DataFrame
#         df = pd.DataFrame(rows)
        
#         # Convert to CSV
#         csv_buffer = StringIO()
#         df.to_csv(csv_buffer, index=False, quoting=csv.QUOTE_ALL)
        
#         return csv_buffer.getvalue()
    
#     @staticmethod
#     def generate_complete_session_export(results: dict) -> dict:
#         """Export everything for complete reproducibility"""
        
#         return {
#             'session_id': hashlib.md5(
#                 f"{results['regulation']}{pd.Timestamp.now()}".encode()
#             ).hexdigest(),
#             'timestamp': pd.Timestamp.now().isoformat(),
#             'regulation': results['regulation'],
#             'document_stats': {
#                 'sections_processed': len(results['sections']),
#                 'policies_generated': len(results['policies']),
#             },
#             'files': {
#                 'type_system': results['type_system'],
#                 'policy_file': results['policy_file'],
#                 'rag_csv': RAGPolicyExporter.generate_rag_csv(results)
#             },
#             'policies': results['policies'],
#             'sections': results['sections']
#         }


class RAGPolicyExporter:
    """Export policies to RAG-friendly CSV format"""
    
    @staticmethod
    def generate_policy_id(regulation: str, section: str) -> str:
        """Generate unique policy ID"""
        section_clean = section.replace(' ', '').replace('.', '').replace('(', '').replace(')', '')
        hash_suffix = hashlib.md5(f"{regulation}{section}".encode()).hexdigest()[:6]
        return f"{regulation.upper()}-{section_clean}-{hash_suffix}"
    
    @staticmethod
    def extract_keywords(statement: str, title: str) -> list:
        """Extract keywords from policy statement"""
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
                     'may', 'shall', 'must', 'should', 'can', 'could', 'will', 'would'}
        
        text = (statement + " " + title).lower()
        words = re.findall(r'\b[a-z]{4,}\b', text)
        
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:10]]
    
    @staticmethod
    def generate_rag_csv(results: dict) -> str:
        """
        Generate RAG CSV from processing results
        
        Args:
            results: Dict with keys: 'regulation', 'policies'
                     where 'policies' is a list of dicts with:
                     - 'section': str
                     - 'title': str
                     - 'statement': str
                     - 'fotl_formula': str
                     - 'conditions': list (optional)
                     - 'action': str (optional)
        """
        
        rows = []
        regulation = results.get('regulation', 'UNKNOWN')
        policies = results.get('policies', [])
        
        for policy in policies:
            policy_id = RAGPolicyExporter.generate_policy_id(
                regulation, 
                policy.get('section', 'N/A')
            )
            
            keywords = RAGPolicyExporter.extract_keywords(
                policy.get('statement', ''),
                policy.get('title', '')
            )
            
            row = {
                'policy_id': policy_id,
                'regulation': regulation,
                'section': policy.get('section', ''),
                'title': policy.get('title', ''),
                'description': policy.get('statement', ''),
                'fotl_formula': policy.get('fotl_formula', ''),
                'keywords': ','.join(keywords),
                'conditions': ','.join(policy.get('conditions', [])),
                'action': policy.get('action', ''),
                'parent_id': '',
                'created_at': pd.Timestamp.now().isoformat()
            }
            
            rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Convert to CSV
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, quoting=csv.QUOTE_ALL)
        
        return csv_buffer.getvalue()


# ============================================
# RAG SEARCH FUNCTIONS
# ============================================

class RAGPolicySearch:
    """Search policies using RAG approach"""
    
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
    
    def search_by_keywords(self, query: str, top_k: int = 5) -> pd.DataFrame:
        """Keyword-based search"""
        query_lower = query.lower()
        
        # Score each policy
        scores = []
        for idx, row in self.df.iterrows():
            score = 0
            
            # Check keywords
            keywords = row['keywords'].split(',')
            for kw in keywords:
                if kw in query_lower:
                    score += 2
            
            # Check title
            if any(word in row['title'].lower() for word in query_lower.split()):
                score += 3
            
            # Check description
            if any(word in row['description'].lower() for word in query_lower.split()):
                score += 1
            
            scores.append(score)
        
        self.df['relevance_score'] = scores
        
        return self.df[self.df['relevance_score'] > 0].nlargest(top_k, 'relevance_score')
    
    def search_by_section(self, section: str) -> pd.DataFrame:
        """Search by section number"""
        return self.df[self.df['section'].str.contains(section, case=False)]
    
    def search_by_regulation(self, regulation: str) -> pd.DataFrame:
        """Filter by regulation"""
        return self.df[self.df['regulation'].str.upper() == regulation.upper()]

# ============================================
# INTEGRATION WITH STREAMLIT
# ============================================

def add_rag_export_to_results(results: dict):
    """Add RAG export options to Streamlit UI"""
    
    st.markdown("---")
    st.markdown("## 🔍 RAG Database Export")
    st.info("Export policies in searchable format for Retrieval-Augmented Generation (RAG)")
    
    # Generate RAG CSV
    rag_csv = RAGPolicyExporter.generate_rag_csv(results)
    
    # Generate complete session export
    complete_export = RAGPolicyExporter.generate_complete_session_export(results)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.download_button(
            label="📊 RAG CSV",
            data=rag_csv,
            file_name=f"{results['regulation'].lower()}_rag.csv",
            mime="text/csv",
            help="Searchable policy database",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            label="📄 Type System",
            data=results['type_system'],
            file_name=f"{results['regulation'].lower()}_types.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        st.download_button(
            label="📜 Policy File",
            data=results['policy_file'],
            file_name=f"{results['regulation'].lower()}_generated.policy",
            mime="text/plain",
            use_container_width=True
        )
    
    with col4:
        st.download_button(
            label="💾 Complete Session",
            data=json.dumps(complete_export, indent=2),
            file_name=f"{results['regulation'].lower()}_session.json",
            mime="application/json",
            help="Everything for reproducibility",
            use_container_width=True
        )
    
    # Preview RAG CSV
    with st.expander("👁️ Preview RAG CSV"):
        df = pd.read_csv(StringIO(rag_csv))
        st.dataframe(df[['policy_id', 'section', 'title', 'keywords']], use_container_width=True)
        
        st.markdown("**Sample Row:**")
        if len(df) > 0:
            sample = df.iloc[0].to_dict()
            st.json(sample)
    
    # RAG Search Demo
    with st.expander("🔍 Test RAG Search"):
        search_query = st.text_input("Search query", "consent")
        
        if search_query:
            searcher = RAGPolicySearch(StringIO(rag_csv))
            results_df = searcher.search_by_keywords(search_query, top_k=3)
            
            if len(results_df) > 0:
                st.success(f"Found {len(results_df)} matching policies")
                for _, row in results_df.iterrows():
                    st.markdown(f"**{row['section']}** - {row['title']} (Score: {row['relevance_score']})")
            else:
                st.warning("No matches found")

# ============================================
# EXAMPLE RAG CSV OUTPUT
# ============================================

"""
Example: gdpr_rag.csv

policy_id,regulation,section,title,description,fotl_formula,keywords,conditions,action,parent_id,created_at
GDPR-Article5-abc123,GDPR,Article 5,Lawfulness of Processing,"Personal data shall be processed lawfully, fairly and in a transparent manner",forall dc ds data...,processing|lawful|transparent|personal|data,dataController|dataSubject|personalData,hasLegalBasis,,2024-12-06T10:30:00
GDPR-Article6-def456,GDPR,Article 6,Legal Basis,"Processing shall be lawful only if at least one of the following applies: consent, contract, legal obligation",forall dc ds purpose...,consent|contract|legal|obligation|basis,dataController|purposeIsPurpose,requiresConsent,,2024-12-06T10:30:01
"""

# ============================================
# USAGE IN RAG SYSTEM
# ============================================

"""
# 1. Build RAG database from multiple regulations
import pandas as pd

hipaa_df = pd.read_csv("hipaa_rag.csv")
gdpr_df = pd.read_csv("gdpr_rag.csv")
ccpa_df = pd.read_csv("ccpa_rag.csv")

all_policies = pd.concat([hipaa_df, gdpr_df, ccpa_df])
all_policies.to_csv("multi_regulation_rag.csv", index=False)

# 2. Use in RAG retrieval
searcher = RAGPolicySearch("multi_regulation_rag.csv")

# Search across all regulations
results = searcher.search_by_keywords("data consent")
# Returns policies from HIPAA, GDPR, CCPA that mention consent

# Search specific regulation
gdpr_results = searcher.search_by_regulation("GDPR")
gdpr_results = searcher.search_by_keywords("data consent", top_k=5)

# 3. Feed to LLM for RAG
context = "\n\n".join([
    f"{row['section']}: {row['description']}"
    for _, row in results.iterrows()
])

prompt = f"
Based on these regulations:
{context}

Question: {user_question}
Answer:
"
"""

