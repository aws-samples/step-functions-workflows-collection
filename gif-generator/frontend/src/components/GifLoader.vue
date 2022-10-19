<template>
  <v-container>
    <v-row>
      <v-card width="800" class="mt-4">
        <v-card-subtitle>
          The Serverless GIF generator creates one JPG per second of video and a GIF animation every configurable 
          period ('snippet size'). Once you have deployed and run the example application, use this frontend to 
          view the results. Configure with your own MP4 URL and settings below, then use the slider to see the 
          frames and GIF at that point in the video. To learn more, see the GitHub repo and companion blog post.
        </v-card-subtitle>     
      </v-card>    
    </v-row>
    <v-row>
      <video-player  class="video-player-box"
        ref="videoPlayer"
        :options="playerOptions"
        :playsinline="true">
      </video-player>
    </v-row>
    <v-row>
      <v-card width="800" >
        <v-card-title>
          Slide to see GIFs and frames
        </v-card-title>

        <v-card-subtitle>
          <v-text-field
            v-model="playerOptions.sources[0].src"
            label="MP4 URL"
          ></v-text-field> 
          <v-row>
            <v-col cols="4">
              <v-text-field
                v-model="gifBucketName"
                label="Bucket name for GIF images"
              ></v-text-field>
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model="snippetSize"
                label="Snippet size (seconds)"
              ></v-text-field>
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model="videoLength"
                label="Video length (seconds)"
              ></v-text-field>                 
            </v-col>
          </v-row>
        </v-card-subtitle>

        <v-card-actions>
          <v-slider
            thumb-label="always"
            hint=""
            min="0"
            :max="videoLength"
            v-model="sliderPos"
            @change="sliderUpdated"
          ></v-slider>
        </v-card-actions>
      </v-card>
    </v-row>
    <!-- The frame and GIF for the selected time -->
    <v-row v-show="sliderPos>0">
      <v-card width="392" class="mt-4">
        <v-card-subtitle>Frame at {{ sliderPos }} seconds</v-card-subtitle>
        <v-img
          max-width="392"
          :src="currentFrameURL"
        ></v-img>
      </v-card>
      <v-card width="392" class="mt-4 ml-4">
        <v-card-subtitle>GIF at {{ snippetStart }} seconds</v-card-subtitle>
        <v-img
          max-width="392"
          :src="currentGIFURL"
        ></v-img>
      </v-card>
    </v-row>
  </v-container>
</template>

<script>
/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

  export default {
    name: 'HelloWorld',

    data() {
      return {
        // videojs options
        playerOptions: {
          width: '800',
          autoplay: true,
          muted: true,
          language: 'en',
          playbackRates: [0.7, 1.0, 1.5, 2.0],
          sources: [{
            type: "video/mp4",
            src: "https://gif-source-bucket.s3.amazonaws.com/{REPLACE}",
          }],
          // poster: "https://surmon-china.github.io/vue-quill-editor/static/images/surmon-1.jpg",
        },
        // Main settings
        snippetSize: 5,
        videoLength: 30,
        sliderPos: 0,
        snippetStart: 0,
        gifBucketName: 'gif-destination-bucket',
        currentFrameURL: '',
        currentGIFURL: ''
      }
    },
    methods: {
      sliderUpdated: function (event) {

        // Get GIF/frame names from settings
        const url = this.playerOptions.sources[0].src
        console.log(url)
        const rawUrl = url.split('//')[1]
        const mp4file = rawUrl.split('/')[1]
        const base = mp4file.split('.')[0]

        this.snippetStart = this.sliderPos - (this.sliderPos % this.snippetSize)
        const frameNum = this.sliderPos - this.snippetStart

        // URLs
        const frameURL = `https://${this.gifBucketName}.s3.amazonaws.com/${base}/${base}-${this.snippetStart}-frame-${frameNum}.jpg`
        const gifURL = `https://${this.gifBucketName}.s3.amazonaws.com/${base}/${base}-${this.snippetStart}.gif`

        this.currentFrameURL = frameURL
        this.currentGIFURL = gifURL
        console.log({event, rawUrl, mp4file, base, frameURL, gifURL, frameNum})
      }
    }
  }
</script>
