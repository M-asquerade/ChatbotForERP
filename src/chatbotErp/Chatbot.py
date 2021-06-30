import json
import re
import sys
import os

from google.cloud import speech
from src.parse_args import args
from src.trans_checker.args import args as cs_args
from src.data_processor.schema_graph import SchemaGraph
from src.chatbotErp.MicrophoneStream import MicrophoneStream
from src.demos.demos import Text2SQLWrapper

#Chat state code
NON_CHAT_STATE=0
CHAT_STATE=1

#Database schema file name
DATABASE_SCHEMA_FILENAME='table_erp.json'

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

class Chatbot():
    '''
    The class for the chatbot (speech recognition and text-to-SQL)
    '''
    def __init__(self, speech_only = False, text_only = False, google_availablity = True):
        print("A Demo for erp system chatbot")
        #Initialize the part Speech to text
        language_code = "en-US"  # a BCP-47 language tag
        # if not (speech_only or text_only):
        #     self.mode = NOMINAL
        # elif speech_only:
        #     self.mode=SPEECH_ONLY
        # elif text_only:
        #     self.mode=TEXT_ONLY
        self.speech_only = speech_only
        self.text_only = text_only

        #Speech recognition should be activated
        if not text_only and google_availablity:
            self.client = speech.SpeechClient()
            self.config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=RATE,
                language_code=language_code,
            )

            self.streaming_config = speech.StreamingRecognitionConfig(
                config=self.config, interim_results=True
            )
            sys.stdout.write("Google Speech-to-text connected\n")
            print("SpeechRecognition started. Say hello to start.")
            sys.stdout.flush()
        elif not google_availablity:
            print("Speech Recognition not available. You can still enter your request by text.")
            self.text_only=True
            sys.stdout.flush()
        else:
            #Text_only mode
            print("You chose the mode with only text_to_sql")

        self.state=NON_CHAT_STATE

        #Initialize the part text to sql
        #the database is limited to product
        if not speech_only:
            db_name = 'product'
            db_path = 'data/spider/database/product/product.sql'
            sys.stdout.write("Text-to-SQL model is initializing.......\n")
            sys.stdout.flush()
            self.schema = SchemaGraph(db_name, db_path=db_path)
            in_json = os.path.join(args.data_dir, DATABASE_SCHEMA_FILENAME)
            with open(in_json) as f:
                tables = json.load(f)
            for table in tables:
                if table['db_id'] == db_name:
                    break
            self.schema.load_data_from_spider_json(table)
            self.schema.pretty_print()
            self.t2sql = Text2SQLWrapper(args, cs_args, self.schema)
            sys.stdout.write("Text_to_sql model initialized\n")
            sys.stdout.flush()
        elif google_availablity:#Speech only
            print("You chose the mode with only speech_to_text True")
        else:#Speech only test mode but google connection not available
            print("Speech Recognition only but google not connected. Exit")
            sys.stdout.flush()
            os._exit(0)


    def text_to_sql(self, text):
        '''
        This function translates the natural language query to SQL.
        The print function makes the output on the commandline. A new redirection can show the query on other software
        or interface.


        :param text: The query of text
        :return: None
        '''
        if text:
            # run Text-to-SQL and Postprocess the SQL translated
            output = self.t2sql.process(text, self.schema.name)
            translatable = output['translatable']
            sql_query = output['sql_query']
            sql_query_opt = output['sql_query_opt']
            confusion_span = output['confuse_span']
            replacement_span = output['replace_span']
            print('Translatable: {}'.format(translatable))
            print('SQL: {}'.format(sql_query))
            # print('Confusion span: {}'.format(confusion_span))
            # print('Replacement span: {}'.format(replacement_span))
            if not translatable:
                print("Javis: Not translatable")
            elif sql_query and isinstance(sql_query, str):
                #Exectue the query.
                result,error_state = self.schema.execute_query(sql_query)
                if error_state:
                    if result:
                        print('The result of the query: {}'.format(result))
                    else:
                        #First transform capital
                        print('SQL Option1: {}'.format(sql_query_opt[0]))
                        print('SQL Option2: {}'.format(sql_query_opt[1]))
                        result1 = self.schema.execute_query(sql_query_opt[0])
                        result2 = self.schema.execute_query(sql_query_opt[1])
                        print("Result Null. These are two potential results.")
                        print("Result Option 1: {}, Result Option 2: {}".format(result1[0],result2[0]))
            sys.stdout.flush()

    def text_to_sql_loop(self):
        '''
        When text to SQL only, this function will be called.
        :return:
        '''
        sys.stdout.write('Enter a natural language question: ')
        sys.stdout.write('> ')
        sys.stdout.flush()
        text = sys.stdin.readline()
        while text:
            self.text_to_sql(text)
            sys.stdout.write('Enter a natural language question: ')
            sys.stdout.write('> ')
            sys.stdout.flush()
            text = sys.stdin.readline()

    def start_conversation(self):
        """
        The conversation loop for the chatbot. This function starts the speech recognition.
        """
        if self.text_only:
            self.text_to_sql_loop()
        else:
            with MicrophoneStream(RATE, CHUNK) as stream:
                while True:
                    audio_generator = stream.generator()
                    requests = (
                        speech.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator
                    )

                    responses = self.client.streaming_recognize(self.streaming_config, requests)

                    # Now, put the transcription responses to use.
                    try:
                        self.listen_print_loop(responses)
                    except Exception:
                        print("Chatbot: Exceeded maximum allowed stream duration of 65 seconds")

    def listen_print_loop(self, responses):
        """Iterates through server responses and prints them.

        The responses passed is a generator that will block until a response
        is provided by the server.

        Each response may contain multiple results, and each result may contain
        multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
        print only the transcription for the top alternative of the top result.

        In this case, responses are provided for interim results as well. If the
        response is an interim one, print a line feed at the end of it, to allow
        the next result to overwrite it, until the response is a final one. For the
        final one, print a newline to preserve the finalized transcription.
        """
        num_chars_printed = 0
        for response in responses:
            if not response.results:
                continue

            # The `results` list is consecutive. For streaming, we only care about
            # the first result being considered, since once it's `is_final`, it
            # moves on to considering the next utterance.
            result = response.results[0]
            if not result.alternatives:
                continue

            # Display the transcription of the top alternative.
            transcript = result.alternatives[0].transcript

            # Display interim results, but with a carriage return at the end of the
            # line, so subsequent lines will overwrite them.
            #
            # If the previous result was longer than this one, we need to print
            # some extra spaces to overwrite the previous result
            overwrite_chars = " " * (num_chars_printed - len(transcript))

            if not result.is_final:
                if self.state == CHAT_STATE:
                    sys.stdout.write(transcript + overwrite_chars + "\r")
                    sys.stdout.flush()
                    num_chars_printed = len(transcript)

            else:
                #Show the last word
                sys.stdout.write(transcript + overwrite_chars + "\r")
                sys.stdout.flush()
                                #
                                # # Exit recognition if any of the transcribed phrases could be
                                # # one of our keywords.
                                # if re.search(r"\b(exit|quit)\b", transcript, re.I):
                                #     print("Exiting..")
                                #     break
                self.state_transition(transcript,overwrite_chars)
                num_chars_printed = 0

    def state_transition(self, transcript, overwrite_chars):
        """
        This function defines the transition of state for the chatbot. There are three states right now: Non_chat_state
        of 'hello' and 'goodbye', chat_state of text_to_SQL. More states are possible to make the chatbot conversational.
        """
        if re.search(r"\b(hello|hi|jarvis)\b", transcript, re.I) and self.state == NON_CHAT_STATE:
            self.state = CHAT_STATE
            sys.stdout.write("You: "+transcript+"\n")
            sys.stdout.write("JARVIS: Hello, Sir\n")
            sys.stdout.flush()
        elif re.search(r"\b(bye|goodbye|see you)\b", transcript, re.I) and self.state == CHAT_STATE:
            self.state = NON_CHAT_STATE
            sys.stdout.write("You:" + transcript + "\n")
            sys.stdout.write("JARVIS: Goodbye, Sir\n")
            sys.stdout.flush()
            return 0
        elif self.state == CHAT_STATE:
            text = transcript + overwrite_chars
            print(text)
            if not self.speech_only:
                self.text_to_sql(text)
            # sys.stdout.write(transcript + overwrite_chars+"\r")
            # sys.stdout.flush()