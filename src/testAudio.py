import sys
import io
import os

import torch

from src.parse_args import args
os.environ['CUDA_VISIBLE_DEVICES'] = '{}'.format(args.gpu)

from src.data_processor.path_utils import get_model_dir
from src.trans_checker.args import args as cs_args
from src.semantic_parser.learn_framework import EncoderDecoderLFramework
from src.chatbotErp.Chatbot import Chatbot
import src.utils.utils as utils


torch.manual_seed(args.seed)
torch.cuda.manual_seed_all(args.seed)
sys.stdout = io.TextIOWrapper(buffer=sys.stdout.buffer,encoding='utf8')
device = torch.device("cuda" if args.gpu == 0 else "cpu")

# Set model ID
args.model_id = utils.model_index[args.model]
assert(args.model_id is not None)


# def main():
#     # See http://g.co/cloud/speech/docs/languages
#     # for a list of supported languages.
#     language_code = "en-US"  # a BCP-47 language tag
#
#     client = speech.SpeechClient()
#     config = speech.RecognitionConfig(
#         encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
#         sample_rate_hertz=RATE,
#         language_code=language_code,
#     )
#
#     streaming_config = speech.StreamingRecognitionConfig(
#         config=config, interim_results=True
#     )
#
#     with MicrophoneStream(RATE, CHUNK) as stream:
#         audio_generator = stream.generator()
#         requests = (
#             speech.StreamingRecognizeRequest(audio_content=content)
#             for content in audio_generator
#         )
#
#         responses = client.streaming_recognize(streaming_config, requests)
#
#         # Now, put the transcription responses to use.
#         listen_print_loop(responses)


def run_chatbot(args):
    cs_args.gpu = args.gpu
    with torch.set_grad_enabled(args.train or args.search_random_seed or args.grid_search or args.fine_tune):
        get_model_dir(args)
        if args.model in ['bridge',
                          'seq2seq',
                          'seq2seq.pg']:
            sp = EncoderDecoderLFramework(args)
        else:
            raise NotImplementedError
        if args.demo_erp:
            chatbot = Chatbot(args.recognition_only,args.text_to_sql_only,args.speech_recognition_available)
            chatbot.start_conversation()


if __name__ == "__main__":
    run_chatbot(args)