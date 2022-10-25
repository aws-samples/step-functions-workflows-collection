/*! Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *  SPDX-License-Identifier: MIT-0
 */

import Vue from 'vue'
import App from './App.vue'
import vuetify from './plugins/vuetify'
import VueVideoPlayer from 'vue-video-player'

Vue.config.productionTip = false
 
// require videojs style
import 'video.js/dist/video-js.css'
Vue.use(VueVideoPlayer, /* {
  options: global default options,
  events: global videojs events
} */)

new Vue({
  vuetify,
  render: h => h(App)
}).$mount('#app')
