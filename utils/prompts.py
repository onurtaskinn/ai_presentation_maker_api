outline_initial_generator_system_message = (
    '''
    You are a presentation outline generator who creates structured, engaging presentation outlines that effectively communicate complex topics.
    '''
)

outline_initial_generator_user_message ='''
    Create a presentation outline on {presentation_topic} with exactly {slide_count} slides.

    Follow these requirements carefully:

    1. Slide Structure:
    - First slide: Introduce the topic with a compelling hook
    - Body slides: Each covers exactly one main concept
    - Last slide: Summarize key points with clear takeaways
    - Each slide must have a clear information hierarchy

    2. Content Organization:
    - Apply "tell-show-tell" principle for key concepts
    - Include audience engagement points every 2-3 slides
    - Break complex topics into digestible chunks
    - Ensure logical flow between slides
    - Include relevant examples or case studies

    3. Slide Focus Requirements:
    - Write each slide_focus as a complete sentence stating the main message
    - Use clear, specific language (avoid buzzwords)
    - Include action verbs in slide titles
    - Make each slide's purpose immediately clear
    - Ensure each slide advances the overall narrative

    Your output must include:
    1. A clear, engaging presentation title
    2. {slide_count} slides, each with:
       - A descriptive title
       - A focused message that supports the main topic
       - A sequential slide number

    IMPORTANT: Generate all content in Turkish language. Respond in fluent, grammatically correct Turkish.

    '''




outline_tester_system_message = '''
You are a presentation outline evaluator who assesses outlines against strict quality and structural criteria to ensure effective communication.
'''

outline_tester_user_message = '''
Evaluate the following presentation outline for quality and effectiveness:

Topic: {presentation_topic}
Title: {presentation_title}
Outline:
{previous_outline_text}

Apply these evaluation criteria:

1. Critical Issues (Any of these results in automatic failure):
- Missing introduction or conclusion slides
- Slides covering multiple unrelated concepts
- Unclear or missing logical flow
- Redundant content across slides
- Vague or unclear slide focus statements

2. Quality Scoring (Total: 100 points)

Structure (40 points):
- Clear topic progression
- One main concept per slide
- Strong opening and closing slides

Content (40 points):
- Specific, actionable slide focuses
- Evidence of audience engagement
- Balanced content distribution
- Clear examples or applications

Practicality (20 points):
- Time management feasibility
- Audience appropriateness
- Presentation flow

Important Rules:
- Do not evaluate the number of slides as this is predefined

Your evaluation must provide:
1. Detailed feedback explaining any issues found
2. Numerical score (0-100) broken down by criteria
'''



outline_fixer_system_message = '''
You are a presentation outline revision specialist who improves presentation outlines based on evaluation feedback while maintaining their core message and structure.
'''

outline_fixer_user_message = '''
Revise the following presentation outline based on the evaluation feedback:

Previous Title: {previous_outline_title}
Previous Outline: {previous_outline_text}
Evaluation Score: {score}
Evaluation Feedback: {feedback}
Slide Count should be: {slide_count}

Follow these revision guidelines:

1. Feedback Implementation Priority:
- Address critical issues first
- Focus on fundamental structure issues for scores below 70
- Enhance content depth and engagement for scores 70-85
- Fine-tune for excellence for scores above 85
- Target highest-point-value issues first

2. Revision Rules:
- Keep the number of slides exactly the same
- Only modify slides mentioned in feedback (unless changes affect flow)
- Maintain successful elements from the original outline
- Ensure all changes directly address feedback points
- Preserve the original presentation's core message

3. Quality Requirements:
- Each slide must have a clear, single focus
- Write all slide_focus statements as complete, actionable sentences
- Maintain logical flow between slides
- Ensure modifications align with presentation goals
- Keep content distribution balanced

4. Revision Constraints:
- Don't change sections that received positive feedback
- Verify that changes don't create new issues
- Consider how modifying one slide affects others
- Maintain consistency across all modifications
- Stay within the original presentation scope

Your output must provide:
1. A revised presentation title (if needed)
2. A complete set of slides, each with:
   - Clear, action-oriented title
   - Focused, complete-sentence message
   - Proper sequential numbering

IMPORTANT: Generate all content in Turkish language. Respond in fluent, grammatically correct Turkish.
'''





content_initial_generator_system_message = (
    '''
        You are an expert in presentation design. Consider the given title and the focus for a slide to provide the necessary content for the slide.
    '''
    )


content_initial_generator_user_message = (
    '''
        You are tasked to generate high quality content for a slide.

        This slide will be part of a presentation titled: {presentation_title}
        The title of the slide is: {slide_title}
        Tha main focus of the slide should be derived from the following statement: {slide_focus}

        Consider both presentation title and the slide title. Make sure that you understand what this slide should focus on.
        Then, follow a step by step approach to decide how you should create content for this slide.

        The slide must be organized as a means to convey information and key messages regarding the main topic of presentation and particular focus of this slide.
        The slide will have some on screen text to let the user follow what is being discussed and also on screen text must help user to get the intended message even if there is no voiceover or images.
        The onscreen text must be concise and prescriptive when it is meaningful.
        The slide will also have some voiceover text that will be read by a speaker.
        The onscreen text and voiceover text must be determined in coherence. Apply the multimedia design principles to generate coherent texts for screen and voiceover.
        The slide will also have an image to enrich its content beyond a text only look.
        I will later use another AI model to generate image for this slide. But I need a detailed and well-written textual image prompt to do that.
        Before writing the prompt, think about the entire context for this slide, presentation, slide title, focus, on screen text and voiceover text.
        First, come up with a good visual idea that would make sense with the rest of the information, context and message we provide here.
        Then express this visual idea with a detailed and descriptive manner as a textual prompt. It is important that your image prompt to be clear, descriptive and detailed.
        Remember that you must specify some visual style as part of the image prompt as well.

        IMPORTANT: Generate all content except the slide_image_prompt in Turkish language. Respond in fluent, grammatically correct Turkish.

        Now take a deep breath and carry out the tasks we set so far.
        You will give your response ensuring that it has all of the following:

        slide_onscreen_text
        slide_voiceover_text
        slide_image_prompt
    '''

)




content_tester_system_message = '''
You are a presentation content validator who evaluates slide content against strict multimedia and technical quality standards.
'''

content_tester_user_message = '''
Evaluate the following slide content for quality, coherence, and technical correctness:

Slide Information:
Presentation Title: {presentation_title}
Slide Title: {slide_title}
Slide Focus: {slide_focus}

Content to Evaluate:
- Onscreen Text: {slide_onscreen_text}
- Voiceover Text: {slide_voiceover_text}
- Image Prompt: {slide_image_prompt}

Evaluation Criteria:

1. Critical Issues (Any of these results in automatic failure, 0 points):
- Misaligned content elements
- Unclear or confusing message
- Missing or incomplete components
- Technical errors in HTML markup or language


2. Quality Scoring (Total: 17 points)

Content Coherence (6 points):
- Alignment between onscreen text, voiceover, and image prompt - (2 points)
- Clear message delivery - (2 points)
- Appropriate level of detail - (1 point)
- Logical flow of information - (1 point)

Multimedia Design (5 points):
- Balance between onscreen and voiceover text - (2 points)
- Onscreen text conciseness - (1 point)
- Voiceover text completeness - (1 point)
- Image prompt relevance and enhancement - (1 point)

Technical Quality (6 points):
- Correct HTML markup usage - (2 points)
- Language consistency - (2 points)
- Image prompt clarity and specificity - (1 points)
- Professional tone - (1 point)

Your evaluation must provide:
1. Comprehensive feedback listing all issues found
2. Detailed score breakdown (0-17) for each criterion

Remember, your evaluation should be strict, don't hesitate to give low scores if you see issues. 

Now take a deep breath and start evaluating the content.
'''



content_fixer_system_message = '''
You are a presentation content revision specialist who improves slide content based on evaluation feedback while maintaining content coherence and multimedia balance.
'''

content_fixer_user_message = '''
Revise the following slide content based on the evaluation feedback:

Original Content:
Presentation Title: {presentation_title}
Slide Title: {slide_title}
Slide Focus: {slide_focus}
Previous Content:
- Onscreen Text: {previous_onscreen_text}
- Voiceover Text: {previous_voiceover_text}
- Image Prompt: {previous_image_prompt}

Evaluation Results:
Score: {score}
Feedback: {feedback}

Follow these revision guidelines:

1. Content Improvement Rules:
- Address each feedback point systematically
- Keep successful elements from the original content
- Ensure all changes align with the slide focus
- Maintain coherence across all content elements
- Verify changes don't create new issues

2. Technical Requirements:
- Use correct HTML markup
- Write detailed, specific image prompts
- Maintain consistent language and tone
- Keep onscreen text concise and impactful
- Ensure voiceover complements visual elements

3. Quality Standards:
- All content must support the core message
- Maintain professional tone throughout
- Balance information across elements
- Preserve the original message while improving delivery

Your output must provide:
1. Revised onscreen text with proper HTML markup
2. Updated voiceover text that complements the visuals
3. Enhanced image prompt that aligns with the content

IMPORTANT: Generate all content except the slide_image_prompt in Turkish language. Respond in fluent, grammatically correct Turkish.

'''




image_tester_system_message = (
    '''
    You are an expert image validator for presentation slides. Your role is to analyze images and provide detailed feedback about their quality and suitability for presentations, ensuring they meet all specified requirements.
    '''
)

image_tester_user_message = (
    '''
    Analyze this image for a presentation slide:

    The slide content is as follows:
    - Onscreen Text: {slide_onscreen_text}
    - Voiceover Text: {slide_voiceover_text}
    - Image Prompt: {slide_image_prompt}

    Evaluate against these criteria:

    CRITICAL ISSUES (Any of these results in automatic rejection):
    1. Contains text or writing within the image
    2. Contains celebrity/famous person likenesses     
    6. Contains inappropriate/offensive content
    7. Has copyright/watermark issues
    8. Shows technical rendering problems
    9. Includes elements not directly supporting the slide's context

    

    SCORING CRITERIA (Total 13 points):

    1. Slide Content Alignment (5 points):
    - Includes elements that align with slide content - (1 point)
    - Matches specified visual style in prompt - (1 point)
    - Contains requested elements - (1 point)
    - Accurate concept representation - (1 point)
    - Proper composition as described - (1 point)

    2. Visual Quality (4 points):
    - Resolution and clarity - (1 point)
    - Color balance and contrast - (1 point)
    - Lighting and shadows - (1 point)
    - Professional appearance - (1 point)

    3. Presentation Suitability (4 points):
    - Fits presentation context - (1 point)
    - Supports slide message - (1 point)
    - Maintains appropriate simplicity - (1 point)
    - Uses minimal, context-appropriate elements - (1 point)
    - Clear focus on key message - (1 point)

    Required Response Format:
    1. Detailed feedback listing specific issues found    
    2. Suggested prompt improvements if needed
    3. Numerical score (0-13)
    

    Remember:
    - Keep images simple and context-appropriate
    - Avoid complex figures
    - Ensure every element serves a purpose
    - Prioritize clarity over artistic complexity

    You have a critical role in ensuring the image aligns with the slide content and enhances the presentation. Therefore be VERY strict in your evaluation.
    Now take a deep breath and start evaluating the image.
    '''
)



image_fixer_system_message = (
    '''
    You are an expert at refining image generation prompts based on feedback. Your role is to improve prompts to create simple, effective presentation visuals.
    '''
)

image_fixer_user_message = (
    '''
    Previous image generation attempt:

    Original image prompt:
    ## {slide_image_prompt}
    ##
    
    Slide Content:
    - Onscreen Text: {slide_onscreen_text}
    - Voiceover Text: {slide_voiceover_text}


    Validation Results:
    - Score: {score}
    - Feedback: {feedback}
    - Improvement Suggestions: {suggestions}

    Create a new, improved prompt following these guidelines:

    1. Critical Requirements:
    - NO text or writing in the image    
    - NO celebrities or famous people
    - Keep visuals simple and minimal
    - Focus only on elements that support the slide's message
    - Avoid complex figures or compositions

    2. Style Requirements:
    - Be specific about visual style
    - Define clear composition
    - Specify colors when relevant
    - Include lighting/mood descriptions
    - Mention quality requirements

    3. Integration Guidelines:
    - Address all feedback points
    - Implement suggested improvements
    - Maintain successful elements from original
    - Ensure presentation suitability

    Provide:
    1. A revised, detailed prompt that addresses all feedback
    2. Brief explanation of key changes made
    '''
)