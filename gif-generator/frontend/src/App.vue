<template>
  <v-app>
    <v-app-bar app color="primary" dark
    >
      <v-toolbar-title>Serverless GIF generator</v-toolbar-title>
      <v-spacer></v-spacer>

      <v-btn href="https://github.com/aws-samples/" target="_blank" text>
        <span class="mr-2">See code on GitHub</span>
        <v-icon>mdi-open-in-new</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main>
      <GifLoader/>
    </v-main>

    <v-footer dark padless class="indigo lighten-1 white--text text-center mt-4">
      <v-col class="text-center white--text" cols="12">
        Questions? Ask <strong><a href="https://twitter.com/jbesw" class="white--text">James Beswick</a></strong>!
      </v-col>
    </v-footer>
  </v-app>
</template>

<script>
/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

import GifLoader from './components/GifLoader'

export default {
  name: 'App',

  components: {
    GifLoader,
  }
}
</script>
