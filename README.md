## Inspiration
Women and girl children in developing nations face significant health challenges, including breast cancer and menstrual problems. These issues are often exacerbated by limited access to healthcare, lack of awareness, and cultural barriers. This results in poor health outcomes, reduced educational opportunities, and social stigma.  

We realized that, AI Technology can play a crucial role in addressing these challenges by providing accessible and affordable self-care solutions. Mobile health applications can offer educational resources on breast health and menstrual hygiene, enabling early detection and management of health issues. Mentoring platforms can facilitate remote consultations with healthcare professionals, improving access to expert care, especially in underserved areas.  

## What it does
1.	Pink Promise has 2 modes. A girl child can use the application for herself needs or there could be a mentor like BlueCross etc., monitoring set of women providing self-guided medical assistance.
2.	The application is powered by most of the top Gemini ai features including the multimodal where we leverage it to extract all information from images like X-rays, pdfs like diagnosis report, video consultations, summarizations
3.	Once data is extracted from all documents, we are creating vector database using google generative ai embeddings.
4.	User authentication is via google oath authentication.
5.	Pink Promise understands sensitive data of women and girl child. So all the data is encoded using google storage.
6.	A mentor can analyze with Gemini the symptoms and provide early diagnosis, precautions to be taken care.
7.	Mentor can also scan individual document and query for details. Let’s say if mentor wants to understand what are the active supplements used from a large documents, Pink Promise gets the results instantly
8.	Pink Promise understand the condition of the patient including sentiment, overall tone, English maturity and emotion which will help the mentor to converse and understand the mentee better.
9.	One of the interesting features we developed using Gemini context caching and all the generated summary is building timeline. mentor can build a dynamic timeline
10.	Pink Promise provides a comprehensive solution based on the analyzed data


## How we built it
We have effectively leveraged Gemini Nano features inclding Translator, Summarization and Prompt API

## Challenges we ran into
1.	Research and understanding women and girl children health care problems in developing nations.
2.	Building a secure solution with all the localized health care documents.
3.	Developing a dictionary based custom search to ensure all the questions are powered by Gemini Context and static answers are retrieved based on the key.
4.	Preview multimodal files and provide individual search on videos, x-rays etc.,
5.	Building a valid summary of summaries for analyzing complex health problems.

## Accomplishments that we're proud of
1.	A very realistic, practical and useful app for women health care.
2.	Discrete data storage and building trust and confidence.
3.	Dynamic alerting as technology improves or when we find solutions at later stage
4.	A fully functional app that can be deployed on GCP.

## What we learned
1.	Infusing Gemini AI at all points and building AI powered intelligent applications.
2.	Building secure and localized AI Applications.

## What's next for Pink Promise
1.	A flutter powered mobile app
2.	Custom RAG with more domain/localized data
3.	Health Emergency alerts based on trends identified


