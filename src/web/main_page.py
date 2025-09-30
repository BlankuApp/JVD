import streamlit as st

st.title("AI-Powered Japanese Learning Platform")
st.markdown(
    """
    Welcome to the future of Japanese language learning! Our platform leverages cutting-edge AI technology 
    to create personalized, adaptive learning experiences that accelerate your JLPT preparation.
    """
)

st.header("📺 YouTube Channel", divider=True)

st.markdown(
    """
    Discover our comprehensive [YouTube channel](https://www.youtube.com/@JapaneseVideoDictionary) featuring 
    **AI-curated Japanese learning content**! Each vocabulary word comes with a dedicated video that explains 
    meaning, usage, and real-world examples in under 3 minutes. Perfect for visual learners who want to see 
    and hear authentic Japanese pronunciation.
    """
)

st.header("📚 JLPT Vocabularies", divider="green")
st.markdown(
    """
    Explore our **comprehensive vocabulary database** featuring thousands of Japanese words categorized by JLPT levels (N5-N1). 
    Each word includes:
    
    - **AI-generated explanations** with cultural context
    - **Smart collocations** and usage patterns
    - **Multi-language translations** in 14+ languages
    - **Integrated YouTube videos** for pronunciation
    - **One-click addition** to your personalized review deck
    
    Build your vocabulary systematically with our intelligent word selection system!
    """
)
if st.button("🚀 Explore AI-Enhanced Vocabularies", type="primary", use_container_width=True):
    st.switch_page("src/web/v.py")


st.header("🧠 AI-Powered Review System", divider="red")
st.markdown(
    """
    Experience the **most advanced spaced repetition system** for Japanese learning! Our AI-driven review platform features:
    
    - **Smart FSRS Algorithm**: Optimized scheduling with 95% retention rate targeting
    - **AI Question Generation**: Dynamic reverse-translation questions tailored to your JLPT level
    - **Intelligent AI Grading**: Instant feedback that understands context, grammar, and meaning
    - **Adaptive Difficulty**: Questions automatically adjust to your learning progress
    - **Multi-language Support**: Questions generated in your preferred language(s)
    - **Contextual Learning**: Each word reviewed with real-world usage examples
    
    Transform your vocabulary retention with scientifically-proven AI methodology!
    """
)
with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        st.image("resources/Review.png", caption="AI generates personalized flashcards with intelligent feedback")
    with col2:
        st.markdown("### ✨ Key AI Features:")
        st.markdown("🤖 **Smart Question Generation**")
        st.markdown("📊 **Automated Progress Tracking**")
        st.markdown("🎯 **Personalized Difficulty**")
        st.markdown("💬 **Instant AI Feedback**")

        if st.button("🎯 Start AI Review", type="primary", use_container_width=True):
            st.switch_page("src/web/review.py")

st.header("✏️ AI Fill-in-the-Blank Exercises", divider="violet")
st.markdown(
    """
    Master Japanese grammar and vocabulary through **AI-generated contextual exercises**! Our intelligent system creates:
    
    - **Dynamic Sentence Generation**: AI crafts natural, grammatically complex sentences using target vocabulary
    - **Adaptive Difficulty Levels**: Exercises automatically match your JLPT level and progress
    - **Contextual Learning**: Each blank tests real-world usage patterns and collocations
    - **Instant Smart Grading**: AI evaluates your answers with detailed explanations
    - **Progressive Complexity**: Questions evolve as your skills improve
    - **Cultural Context**: Sentences reflect authentic Japanese communication patterns
    
    Practice makes perfect - especially with AI-powered precision!
    """
)
with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        st.image(
            "resources/FillInTheBlank.png",
            caption="AI creates contextual exercises that adapt to your learning level",
        )
    with col2:
        st.markdown("### 🎯 Smart Features:")
        st.markdown("🤖 **AI Sentence Creation**")
        st.markdown("📝 **Contextual Blanks**")
        st.markdown("🎚️ **Adaptive Difficulty**")
        st.markdown("✅ **Intelligent Grading**")

        if st.button("📝 Try AI Exercises", type="secondary", use_container_width=True):
            st.switch_page("src/web/fill_in_the_blank.py")

st.divider()

# Add a call-to-action section
st.markdown("### 🚀 Ready to Accelerate Your Japanese Learning?")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📚 Browse Vocabulary", use_container_width=True):
        st.switch_page("src/web/v.py")

with col2:
    if st.button("🧠 Start AI Review", type="primary", use_container_width=True):
        st.switch_page("src/web/review.py")

with col3:
    if st.button("✏️ Practice Exercises", use_container_width=True):
        st.switch_page("src/web/fill_in_the_blank.py")
