<script lang="ts">
	import { page } from '$app/stores';

	import Channel from '$features/channels/Channel.svelte';
</script>

<Channel id={$page.params.id} />
